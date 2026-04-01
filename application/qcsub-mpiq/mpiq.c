#include "mpiq.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/stat.h>
#include <arpa/inet.h>

static int send_file(int socket, const char *filepath, const char *filename);
static int scan_files(const char *folder_path, char **files, int *count);
static int recv_file(int client_socket, const char *output_dir, const char *filename, long filesize);
static int recv_file_with_path(int client_socket, const char *output_dir, const char *filename, long filesize);
static int send_files_with_header(const char *ip, int port, const char *folder_path, const char *header_prefix, int subcircuit_idx);

int MPIQ_Send(const char *ip, int port, const char *folder_path, int subcircuit_idx)
{
    return send_files_with_header(ip, port, folder_path, "FOLDER", subcircuit_idx);
}

int MPIQ_Send_Results(const char *ip, int port, const char *folder_path)
{
    return send_files_with_header(ip, port, folder_path, "RESULTS", -1);
}

int MPIQ_Recv(int port, const char *output_dir, int expected_subcircuit_idx)
{
    int server_fd, client_fd;
    struct sockaddr_in server_addr, client_addr;
    socklen_t client_len = sizeof(client_addr);

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0)
    {
        perror("Socket creation failed");
        return -1;
    }

    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0)
    {
        perror("Setsockopt failed");
        close(server_fd);
        return -1;
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
    {
        perror("Bind failed");
        close(server_fd);
        return -1;
    }

    if (listen(server_fd, 1) < 0)
    {
        perror("Listen failed");
        close(server_fd);
        return -1;
    }

    printf("Waiting for connections on port %d...\n", port);

    client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &client_len);
    if (client_fd < 0)
    {
        perror("Accept failed");
        close(server_fd);
        return -1;
    }

    printf("Connection accepted from %s:%d\n",
           inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

    char buffer[MPIQ_BUFFER_SIZE];
    int bytes_received;

    char len_header[9];
    len_header[8] = '\0';
    if (recv(client_fd, len_header, 8, 0) != 8)
    {
        perror("Failed to receive header length");
        close(client_fd);
        close(server_fd);
        return -1;
    }
    int header_len = atoi(len_header);

    if (recv(client_fd, buffer, header_len, 0) != header_len)
    {
        perror("Failed to receive header");
        close(client_fd);
        close(server_fd);
        return -1;
    }
    buffer[header_len] = '\0';

    int file_count = 0;
    int is_results = 0;
    int received_subcircuit_idx = -1;

    if (sscanf(buffer, "FOLDER:%d:%d", &file_count, &received_subcircuit_idx) == 2)
    {
        is_results = 0;
        printf("Expected subcircuit_%d, received subcircuit_%d\n", expected_subcircuit_idx, received_subcircuit_idx);
        
        // 验证子电路索引是否匹配
        if (received_subcircuit_idx != expected_subcircuit_idx)
        {
            printf("Warning: Subcircuit index mismatch! Expected %d, got %d\n", expected_subcircuit_idx, received_subcircuit_idx);
            // 可以选择在这里返回错误，或者继续处理
        }
    }
    else if (sscanf(buffer, "RESULTS:%d", &file_count) == 1)
    {
        is_results = 1;
    }
    else
    {
        printf("Invalid header: %s\n", buffer);
        close(client_fd);
        close(server_fd);
        return -1;
    }

    printf("Receiving %d files for subcircuit_%d...\n", file_count, received_subcircuit_idx);

    mkdir(output_dir, 0755);

    for (int i = 0; i < file_count; i++)
    {
        if (recv(client_fd, len_header, 8, 0) != 8)
        {
            perror("Failed to receive file header length");
            close(client_fd);
            close(server_fd);
            return -1;
        }
        header_len = atoi(len_header);

        if (recv(client_fd, buffer, header_len, 0) != header_len)
        {
            perror("Failed to receive file header");
            close(client_fd);
            close(server_fd);
            return -1;
        }
        buffer[header_len] = '\0';

        char filename[256];
        long filesize = 0;
        if (sscanf(buffer, "FILE:%[^:]:%ld", filename, &filesize) != 2)
        {
            printf("Invalid file header: %s\n", buffer);
            close(client_fd);
            close(server_fd);
            return -1;
        }

        printf("  Receiving: %s (%ld bytes)\n", filename, filesize);

        if (is_results)
        {
            if (recv_file_with_path(client_fd, output_dir, filename, filesize) < 0)
            {
                close(client_fd);
                close(server_fd);
                return -1;
            }
        }
        else
        {
            if (recv_file(client_fd, output_dir, filename, filesize) < 0)
            {
                close(client_fd);
                close(server_fd);
                return -1;
            }
        }
    }

    printf("All files received successfully!\n");

    close(client_fd);
    close(server_fd);

    return 0;
}

static int send_files_with_header(const char *ip, int port, const char *folder_path, const char *header_prefix, int subcircuit_idx)
{
    int sock = -1;
    int retries = 0;
    const int MAX_RETRIES = 30;         // 最多重试30次
    const int RETRY_INTERVAL = 1000000; // 1秒

    while (retries < MAX_RETRIES)
    {
        sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0)
        {
            perror("Socket creation failed");
            return -1;
        }

        struct sockaddr_in server_addr;
        memset(&server_addr, 0, sizeof(server_addr));
        server_addr.sin_family = AF_INET;
        server_addr.sin_port = htons(port);
        server_addr.sin_addr.s_addr = inet_addr(ip);

        if (connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
        {
            perror("Connection failed");
            close(sock);
            retries++;
            printf("Retrying connection... (%d/%d)\n", retries, MAX_RETRIES);
            usleep(RETRY_INTERVAL);
            continue;
        }
        break;
    }

    if (sock < 0 || retries >= MAX_RETRIES)
    {
        fprintf(stderr, "Failed to connect after %d retries\n", MAX_RETRIES);
        return -1;
    }

    char *files[MAX_FILES];
    int file_count = 0;

    if (scan_files(folder_path, files, &file_count) < 0)
    {
        close(sock);
        return -1;
    }

    char header[512];
    int header_len = snprintf(header, sizeof(header), "%s:%d:%d", header_prefix, file_count, subcircuit_idx);
    char len_header[32];
    int len_len = snprintf(len_header, sizeof(len_header), "%08d", header_len);

    send(sock, len_header, 8, 0);
    send(sock, header, header_len, 0);

    usleep(50000);

    for (int i = 0; i < file_count; i++)
    {
        char *filename = strrchr(files[i], '/');
        if (filename != NULL)
        {
            filename++;
        }
        else
        {
            filename = files[i];
        }

        if (send_file(sock, files[i], filename) < 0)
        {
            close(sock);
            return -1;
        }
    }

    for (int i = 0; i < file_count; i++)
    {
        free(files[i]);
    }

    printf("All files sent successfully! (subcircuit_%d)\n", subcircuit_idx);

    close(sock);
    return 0;
}

static int send_file(int socket, const char *filepath, const char *filename)
{
    FILE *fp = fopen(filepath, "rb");
    if (fp == NULL)
    {
        perror("Failed to open file");
        return -1;
    }

    fseek(fp, 0, SEEK_END);
    long filesize = ftell(fp);
    fseek(fp, 0, SEEK_SET);

    char header[512];
    int header_len = snprintf(header, sizeof(header), "FILE:%s:%ld", filename, filesize);
    char len_header[32];
    int len_len = snprintf(len_header, sizeof(len_header), "%08d", header_len);

    send(socket, len_header, 8, 0);
    send(socket, header, header_len, 0);

    usleep(10000);

    char buffer[MPIQ_BUFFER_SIZE];
    size_t bytes_read;
    while ((bytes_read = fread(buffer, 1, MPIQ_BUFFER_SIZE, fp)) > 0)
    {
        if (send(socket, buffer, bytes_read, 0) < 0)
        {
            perror("Failed to send file data");
            fclose(fp);
            return -1;
        }
    }

    fclose(fp);
    printf("  Sent: %s (%ld bytes)\n", filename, filesize);
    return 0;
}

static int scan_files(const char *folder_path, char **files, int *count)
{
    DIR *dir = opendir(folder_path);
    if (dir == NULL)
    {
        perror("Failed to open directory");
        return -1;
    }

    struct dirent *entry;
    *count = 0;

    while ((entry = readdir(dir)) != NULL && *count < MAX_FILES)
    {
        if (entry->d_type == DT_REG)
        {
            files[*count] = (char *)malloc(MAX_PATH_LEN);
            snprintf(files[*count], MAX_PATH_LEN, "%s/%s", folder_path, entry->d_name);
            (*count)++;
        }
    }

    closedir(dir);
    return 0;
}

static int recv_file(int client_socket, const char *output_dir, const char *filename, long filesize)
{
    char filepath[MAX_PATH_LEN];
    snprintf(filepath, sizeof(filepath), "%s/%s", output_dir, filename);

    FILE *fp = fopen(filepath, "wb");
    if (fp == NULL)
    {
        perror("Failed to create file");
        return -1;
    }

    char buffer[MPIQ_BUFFER_SIZE];
    long total_received = 0;
    int bytes_received;

    while (total_received < filesize)
    {
        int to_receive = (filesize - total_received) > MPIQ_BUFFER_SIZE ? MPIQ_BUFFER_SIZE : (filesize - total_received);
        bytes_received = recv(client_socket, buffer, to_receive, 0);

        if (bytes_received <= 0)
        {
            perror("Failed to receive file data");
            fclose(fp);
            return -1;
        }

        fwrite(buffer, 1, bytes_received, fp);
        total_received += bytes_received;
    }

    fclose(fp);
    printf("    Saved: %s\n", filepath);
    return 0;
}

static int recv_file_with_path(int client_socket, const char *output_dir, const char *filename, long filesize)
{
    char filepath[MAX_PATH_LEN];
    snprintf(filepath, sizeof(filepath), "%s/%s", output_dir, filename);

    char *dirpath = strdup(filepath);
    char *last_slash = strrchr(dirpath, '/');
    if (last_slash != NULL)
    {
        *last_slash = '\0';
        mkdir(dirpath, 0755);
    }
    free(dirpath);

    FILE *fp = fopen(filepath, "wb");
    if (fp == NULL)
    {
        perror("Failed to create file");
        return -1;
    }

    char buffer2[MPIQ_BUFFER_SIZE];
    long total_received = 0;
    int bytes_received;

    while (total_received < filesize)
    {
        int to_receive = (filesize - total_received) > MPIQ_BUFFER_SIZE ? MPIQ_BUFFER_SIZE : (filesize - total_received);
        bytes_received = recv(client_socket, buffer2, to_receive, 0);

        if (bytes_received <= 0)
        {
            perror("Failed to receive file data");
            fclose(fp);
            return -1;
        }

        fwrite(buffer2, 1, bytes_received, fp);
        total_received += bytes_received;
    }

    fclose(fp);
    printf("    Saved: %s\n", filepath);
    return 0;
}

/* ============================================================
 * Quantum-level waveform data transfer (merged from ./MPIQ/)
 * ============================================================ */

/**
 * @brief Reliable send: loop until all bytes are sent
 * @return 0 on success, -1 on error
 */
static int qsend_all(int sock, const void *buf, size_t len, int flags)
{
    const char *p = (const char *)buf;
    size_t remaining = len;
    while (remaining > 0)
    {
        ssize_t sent = send(sock, p, remaining, flags);
        if (sent <= 0)
            return -1;
        p += sent;
        remaining -= sent;
    }
    return 0;
}

/**
 * @brief Reliable recv: loop until all bytes are received
 * @return 0 on success, -1 on error or connection closed
 */
static int qrecv_all(int sock, void *buf, size_t len, int flags)
{
    char *p = (char *)buf;
    size_t remaining = len;
    while (remaining > 0)
    {
        ssize_t got = recv(sock, p, remaining, flags);
        if (got <= 0)
            return -1;
        p += got;
        remaining -= got;
    }
    return 0;
}

/**
 * @brief Print qubit waveform data in a compressed format
 *
 * Merged from ./MPIQ/qubit_print.c. Consecutive repeated values are
 * compressed into "repeat N times" summaries for readability.
 */
void qubit_print(char ***qubit, int qubit_count, int *arry_counts)
{
    for (int i = 0; i < qubit_count; i++)
    {
        int repetition = 0;
        for (int j = 0; j < arry_counts[i]; j++)
        {
            if (j == 0)
            {
                printf("qubit_%d: %s ", i, qubit[i][j]);
                if (strcmp(qubit[i][j], qubit[i][j + 1]) == 0)
                {
                    repetition++;
                }
            }
            else if (j == (arry_counts[i] - 1))
            {
                if (repetition == 0)
                    printf("%s\n", qubit[i][j]);
                else
                {
                    repetition++;
                    printf("repeat %d times\n", repetition);
                }
            }
            else
            {
                if (repetition == 0)
                {
                    printf("%s ", qubit[i][j]);
                    if (strcmp(qubit[i][j], qubit[i][j + 1]) == 0)
                    {
                        repetition++;
                    }
                }
                else
                {
                    repetition++;
                    if (strcmp(qubit[i][j], qubit[i][j + 1]))
                    {
                        printf("repeat %d times ", repetition);
                        repetition = 0;
                    }
                }
            }
        }
    }
}

/**
 * @brief Send quantum bit waveform data to a quantum processing board
 *
 * Merged from ./MPIQ/MPIQ_Send.c. Establishes a TCP connection and sends
 * quantum bit waveform data using a reliable request-response protocol.
 * Port = 5000 + card_id.
 *
 * @param qubit_count  Number of quantum bits to send
 * @param arry_counts  Array: number of data points per qubit
 * @param qubit        3D array: qubit[qubit_idx][point_idx] waveform string
 * @param ip           IP address of the quantum processing board
 * @param card_id      Card ID (port = 5000 + card_id)
 * @param comm         MPIQ_Comm communication domain
 * @return 0 on success, -1 on error
 */
int MPIQ_SendQubits(int qubit_count, int *arry_counts, char ***qubit,
                    char *ip, int card_id, MPIQ_Comm comm)
{
    int sock = 0;
    struct sockaddr_in serv_addr;
    char buffer[MPIQ_LARGE_BUFFER_SIZE] = {0};

    /* Create TCP socket */
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
    {
        perror("socket creation failed");
        return -1;
    }

    /* Configure server address */
    serv_addr.sin_family = AF_INET;
    int PORT = 5000 + card_id;
    serv_addr.sin_port = htons(PORT);

    if (inet_pton(AF_INET, ip, &serv_addr.sin_addr) <= 0)
    {
        perror("invalid server IP address");
        close(sock);
        return -1;
    }

    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
    {
        perror("Failed to connect to server (please check if IP and port are correct)");
        close(sock);
        return -1;
    }
    printf("Successfully connected to server (IP: %s, Port: %d)\n", ip, PORT);

    /* Send communication mode to initiate protocol */
    char mode[] = "request for send";
    qsend_all(sock, mode, sizeof(mode), 0);

    /* Wait for acknowledgment from server */
    while (1)
    {
        ssize_t valread = qrecv_all(sock, buffer, MPIQ_LARGE_BUFFER_SIZE - 1, 0);
        if (valread < 0) { close(sock); return -1; }
        buffer[MPIQ_LARGE_BUFFER_SIZE - 1] = '\0';
        if (strcmp(buffer, "right") == 0)
            break;
    }
    memset(buffer, 0, MPIQ_LARGE_BUFFER_SIZE);

    /* Send number of quantum bits */
    qubit_print(qubit, qubit_count, arry_counts);
    char count_str[100];
    sprintf(count_str, "%d", qubit_count);
    qsend_all(sock, count_str, sizeof(count_str), 0);

    /* Wait for acknowledgment */
    while (1)
    {
        ssize_t valread = qrecv_all(sock, buffer, MPIQ_LARGE_BUFFER_SIZE - 1, 0);
        if (valread < 0) { close(sock); return -1; }
        buffer[MPIQ_LARGE_BUFFER_SIZE - 1] = '\0';
        if (strcmp(buffer, "right") == 0)
            break;
    }
    memset(buffer, 0, MPIQ_LARGE_BUFFER_SIZE);

    /* Send quantum bit waveform data for each quantum bit */
    for (int i = 0; i < qubit_count; i++)
    {
        /* Send the number of data points for this quantum bit */
        sprintf(count_str, "%d", arry_counts[i]);
        qsend_all(sock, count_str, sizeof(count_str), 0);

        /* Wait for acknowledgment */
        while (1)
        {
            ssize_t valread = qrecv_all(sock, buffer, MPIQ_LARGE_BUFFER_SIZE - 1, 0);
            if (valread < 0) { close(sock); return -1; }
            buffer[MPIQ_LARGE_BUFFER_SIZE - 1] = '\0';
            if (strcmp(buffer, "right") == 0)
                break;
        }
        memset(buffer, 0, MPIQ_LARGE_BUFFER_SIZE);
        memset(count_str, 0, sizeof(count_str));

        /* Send each waveform data point */
        for (int j = 0; j < arry_counts[i]; j++)
        {
            qsend_all(sock, qubit[i][j], 25, 0);

            while (1)
            {
                ssize_t valread = qrecv_all(sock, buffer, MPIQ_LARGE_BUFFER_SIZE - 1, 0);
                if (valread < 0) { close(sock); return -1; }
                buffer[MPIQ_LARGE_BUFFER_SIZE - 1] = '\0';
                if (strcmp(buffer, "right") == 0)
                    break;
            }
            memset(buffer, 0, MPIQ_LARGE_BUFFER_SIZE);
        }
    }

    /* Write send data to file */
    FILE *fp = fopen("../data/send_data.txt", "w");
    if (fp != NULL)
    {
        fprintf(fp, "%d\n", qubit_count);
        for (int i = 0; i < qubit_count; i++)
            fprintf(fp, "%d ", arry_counts[i]);
        fprintf(fp, "\n");
        for (int i = 0; i < qubit_count; i++)
        {
            for (int j = 0; j < arry_counts[i]; j++)
                fprintf(fp, "%s ", qubit[i][j]);
            fprintf(fp, "\n");
        }
        fclose(fp);
        printf("Successfully wrote send data to ../data/send_data.txt\n");
    }

    close(sock);
    return 0;
}

/**
 * @brief Receive quantum bit waveform data from a quantum processing board
 *
 * Merged from ./MPIQ/MPIQ_Recv.c. Establishes a TCP connection and receives
 * qubit waveform data using a reliable request-response protocol with
 * comma-separated value parsing. Port = 5000 + card_id.
 *
 * @param ip           IP address of the quantum processing board
 * @param card_id      Card ID (port = 5000 + card_id)
 * @param qubit_count  [out] Number of quantum bits received
 * @param arry_counts  [out] Array: data points per qubit (caller must free)
 * @param comm         MPIQ_Comm communication domain
 * @return 3D array of waveform data (caller must free), or NULL on error
 */
char ***MPIQ_RecvQubits(char *ip, int card_id, int *qubit_count,
                        int **arry_counts, MPIQ_Comm comm)
{
    int sock = 0;
    struct sockaddr_in serv_addr;
    char buffer[MPIQ_LARGE_BUFFER_SIZE] = {0};
    char send_message[] = "right";
    char ***result = NULL;
    int *a_counts = NULL;

    /* Create TCP socket */
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
    {
        perror("socket creation failed");
        return NULL;
    }

    /* Configure server address */
    serv_addr.sin_family = AF_INET;
    int PORT = 5000 + card_id;
    serv_addr.sin_port = htons(PORT);

    if (inet_pton(AF_INET, ip, &serv_addr.sin_addr) <= 0)
    {
        perror("invalid server IP address");
        close(sock);
        return NULL;
    }

    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
    {
        perror("Failed to connect to server (please check if IP and port are correct)");
        close(sock);
        return NULL;
    }
    printf("Successfully connected to server (IP: %s, Port: %d)\n", ip, PORT);

    /* Send communication mode to request results */
    char mode[] = "request for result";
    qsend_all(sock, mode, sizeof(mode), 0);

    /* Wait for acknowledgment from server */
    while (1)
    {
        int ret = qrecv_all(sock, buffer, MPIQ_LARGE_BUFFER_SIZE - 1, 0);
        if (ret < 0) { close(sock); return NULL; }
        buffer[MPIQ_LARGE_BUFFER_SIZE - 1] = '\0';
        if (strcmp(buffer, "right") == 0)
            break;
    }

    int qubit_times = 0;

    memset(buffer, 0, MPIQ_LARGE_BUFFER_SIZE);
    qsend_all(sock, send_message, sizeof(send_message), 0);

    /* Receive first data packet */
    ssize_t valread = qrecv_all(sock, buffer, MPIQ_LARGE_BUFFER_SIZE - 1, 0);
    if (valread < 0) { close(sock); return NULL; }
    buffer[MPIQ_LARGE_BUFFER_SIZE - 1] = '\0';

    /* Receive until "exit" message */
    while (strcmp(buffer, "exit") != 0)
    {
        char **wave_arry = NULL;
        char *token;

        result = (char ***)realloc(result, (qubit_times + 1) * sizeof(char **));
        wave_arry = (char **)realloc(wave_arry, sizeof(char *));
        wave_arry[0] = (char *)malloc(25 * sizeof(char));

        buffer[strcspn(buffer, "\n")] = '\0';
        token = strtok(buffer, ",");
        strcpy(wave_arry[0], token);

        int arry_num = 1;
        token = strtok(NULL, ",");
        while (token != NULL)
        {
            wave_arry = (char **)realloc(wave_arry, (arry_num + 1) * sizeof(char *));
            wave_arry[arry_num] = (char *)malloc(25 * sizeof(char));
            strcpy(wave_arry[arry_num], token);
            arry_num++;
            token = strtok(NULL, ",");
        }

        memset(buffer, 0, MPIQ_LARGE_BUFFER_SIZE);
        qsend_all(sock, send_message, sizeof(send_message), 0);

        result[qubit_times] = wave_arry;
        a_counts = (int *)realloc(a_counts, (qubit_times + 1) * sizeof(int));
        a_counts[qubit_times] = arry_num;

        qubit_times++;

        valread = qrecv_all(sock, buffer, MPIQ_LARGE_BUFFER_SIZE - 1, 0);
        if (valread < 0) { close(sock); return NULL; }
        buffer[MPIQ_LARGE_BUFFER_SIZE - 1] = '\0';
    }

    /* Final acknowledgment */
    memset(buffer, 0, MPIQ_LARGE_BUFFER_SIZE);
    qsend_all(sock, send_message, sizeof(send_message), 0);

    close(sock);

    /* Update output parameters */
    *qubit_count = qubit_times;
    *arry_counts = a_counts;

    /* Write received data to file */
    FILE *fp = fopen("../data/recv_result.txt", "w");
    if (fp != NULL)
    {
        fprintf(fp, "%d\n", qubit_times);
        for (int i = 0; i < qubit_times; i++)
            fprintf(fp, "%d ", a_counts[i]);
        fprintf(fp, "\n");
        for (int i = 0; i < qubit_times; i++)
        {
            for (int j = 0; j < a_counts[i]; j++)
                fprintf(fp, "%s ", result[i][j]);
            fprintf(fp, "\n");
        }
        fclose(fp);
        printf("Successfully wrote received data to ../data/recv_result.txt\n");
    }

    return result;
}

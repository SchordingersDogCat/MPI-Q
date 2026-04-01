/**
 * @file MPIQ_recv.c
 * @brief MPIQ data receiving module for quantum processing board communication
 *
 * This module implements the MPIQ_Recv function, which is responsible for
 * receiving quantum bit waveform data from quantum processing boards to classical
 * processes. It establishes TCP/IP connections, implements a reliable
 * request-response protocol, and processes the received data according to the
 * MPIQ data format specifications.
 *
 * Key functionalities include:
 * - TCP socket creation and configuration
 * - Connection establishment with quantum processing boards
 * - Reception of quantum bit waveform data using a structured protocol
 * - Parsing of comma-separated values to extract individual waveform points
 * - Dynamic memory allocation for storing received data
 *
 * This module is part of the MPIQ library, which extends MPI functionality
 * for quantum-classical hybrid computing applications.
 */

#include "MPIQ.h"

/**
 * @brief Reliable send: loop until all bytes are sent
 * @return 0 on success, -1 on error
 */
static int send_all(int sock, const void *buf, size_t len, int flags)
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
static int recv_all(int sock, void *buf, size_t len, int flags)
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
 * @brief Receive quantum bit waveform data from a quantum processing board
 *
 * This function establishes a TCP connection to a quantum processing board and
 * receives quantum bit waveform data using a reliable request-response protocol.
 * It sends a request for results, then processes the received comma-separated
 * values to extract individual quantum bit waveform data points.
 *
 * @param[in] ip IP address of the quantum processing board
 * @param[in] card_id Identifier of the quantum processing board
 * @param[in] comm MPIQ_Comm structure defining the communication domain
 * @param[out] qubit_count Number of quantum bits received
 * @param[out] arry_counts Array containing the number of data points for each quantum bit
 * @return Three-dimensional array containing the received quantum bit waveform data,
 *         or NULL on error
 *
 * @note The function uses port 5000 + card_id for communication
 * @note The caller is responsible for freeing the returned memory
 * @attention Memory is dynamically allocated for the returned data structures
 */
char ***MPIQ_Recv(char *ip, int card_id, int *qubit_count, int **arry_counts, MPIQ_Comm comm)
{
    int sock = 0;                  // Socket file descriptor
    struct sockaddr_in serv_addr;  // Server address structure
    char buffer[BUFFERSIZE] = {0}; // Communication buffer
    char send_message[] = "right"; // Acknowledgment message
    char ***result = NULL;         // 3D array to store received quantum bit data
    int *a_counts = NULL;          // Array to store data point counts

    // Create TCP socket for communication
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
    {
        perror("socket creation failed");
        return NULL;
    }
    // Configure server address structure
    serv_addr.sin_family = AF_INET;
    int PORT;
    PORT = 5000 + card_id; // Calculate port based on card ID
    serv_addr.sin_port = htons(PORT);

    // Convert server IP address to network byte order
    if (inet_pton(AF_INET, ip, &serv_addr.sin_addr) <= 0)
    {
        perror("invalid server IP address");
        return NULL;
    }
    // Connect to the quantum processing board
    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
    {
        perror("Failed to connect to server (please check if IP and port are correct)");
        return NULL;
    }
    printf("Successfully connected to server (IP: %s, Port: %d)\n", ip, PORT);
    // Send communication mode to request results
    char mode[] = "request for result";
    send_all(sock, mode, sizeof(mode), 0);

    // Wait for acknowledgment from server
    while (1)
    {
        int ret = recv_all(sock, buffer, BUFFERSIZE - 1, 0);
        if (ret < 0) { close(sock); return NULL; }
        buffer[BUFFERSIZE - 1] = '\0';
        if (strcmp(buffer, "right") == 0)
            break;
    }
    // Initialize counter for received quantum bits
    int qubit_times = 0;

    // Clear buffer and send acknowledgment
    memset(buffer, 0, BUFFERSIZE);
    send_all(sock, send_message, sizeof(send_message), 0);

    // Receive first data packet
    ssize_t valread = recv_all(sock, buffer, BUFFERSIZE - 1, 0);
    if (valread < 0) { close(sock); return NULL; }
    buffer[BUFFERSIZE - 1] = '\0';
    // printf("message is:%s\n", buffer);

    // Receive quantum bit waveform data until "exit" message is received
    while (strcmp(buffer, "exit") != 0)
    {
        char **wave_arry = NULL; // 2D array to store waveform data for current quantum bit
        char *token;             // Token for string splitting

        // Allocate memory for new quantum bit in the result array
        result = (char ***)realloc(result, (qubit_times + 1) * sizeof(char **));

        // Allocate memory for first data point
        wave_arry = (char **)realloc(wave_arry, (1) * sizeof(char *));
        wave_arry[0] = (char *)malloc(25 * sizeof(char));

        // Remove newline character from buffer
        buffer[strcspn(buffer, "\n")] = '\0';
        // Split the received buffer to extract individual waveform data points
        token = strtok(buffer, ",");
        strcpy(wave_arry[0], token);

        // Initialize data point counter
        int arry_num = 1;
        // Process remaining data points in the current buffer
        token = strtok(NULL, ",");
        while (token != NULL)
        {
            // Allocate memory for next data point
            wave_arry = (char **)realloc(wave_arry, (arry_num + 1) * sizeof(char *));
            wave_arry[arry_num] = (char *)malloc(25 * sizeof(char));
            strcpy(wave_arry[arry_num], token);
            arry_num++;
            token = strtok(NULL, ",");
        }
        // Prepare for next iteration
        memset(buffer, 0, BUFFERSIZE);
        send_all(sock, send_message, sizeof(send_message), 0);

        // Store the received waveform array and its size
        result[qubit_times] = wave_arry;
    // BUG FIX (v29->v30): The original code was missing sizeof(int), resulting in
    // insufficient allocation bytes and causing a heap overflow.
    a_counts = (int *)realloc(a_counts, (qubit_times + 1) * sizeof(int));
        a_counts[qubit_times] = arry_num;

        // Move to next quantum bit
        qubit_times++;

        // Receive next data packet
        valread = recv_all(sock, buffer, BUFFERSIZE - 1, 0);
        if (valread < 0) { close(sock); return NULL; }
        buffer[BUFFERSIZE - 1] = '\0';
        // printf("message is:%s\n", buffer);
    }
    // Final acknowledgment after receiving all data
    memset(buffer, 0, BUFFERSIZE);
    send_all(sock, send_message, sizeof(send_message), 0);

    // Close the socket connection
    close(sock);

    // Update output parameters with received data
    *qubit_count = qubit_times;
    *arry_counts = a_counts;

    // Write received quantum bit data to file
    FILE *fp;
    char filename[] = "../data/recv_result.txt";

    fp = fopen(filename, "w");
    if (fp == NULL)
    {
        perror("Failed to open file for writing");
        // Continue execution even if file writing fails
    }
    else
    {
        // Write qubit count
        fprintf(fp, "%d\n", qubit_times);

        // Write data point counts for each qubit
        for (int i = 0; i < qubit_times; i++)
        {
            fprintf(fp, "%d ", a_counts[i]);
        }
        fprintf(fp, "\n");

        // Write the actual quantum bit waveform data
        for (int i = 0; i < qubit_times; i++)
        {
            for (int j = 0; j < a_counts[i]; j++)
            {
                fprintf(fp, "%s ", result[i][j]);
            }
            fprintf(fp, "\n");
        }

        fclose(fp);
        printf("Successfully wrote received data to %s\n", filename);
    }

    // Return the received quantum bit waveform data
    return result;
}

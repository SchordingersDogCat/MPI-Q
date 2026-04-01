/**
 * @file MPIQ_send.c
 * @brief MPIQ data sending module for quantum processing board communication
 *
 * This module implements the MPIQ_Send function, which is responsible for
 * transmitting quantum bit waveform data from classical processes to quantum
 * processing boards. It establishes TCP/IP connections, implements a reliable
 * request-response protocol, and ensures data integrity during transmission.
 *
 * Key functionalities include:
 * - TCP socket creation and configuration
 * - Connection establishment with quantum processing boards
 * - Transmission of quantum bit waveform data using a structured protocol
 * - Request-acknowledgment mechanism for reliable communication
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
 * @brief Send quantum bit waveform data to a quantum processing board
 *
 * This function establishes a TCP connection to a quantum processing board and
 * sends quantum bit waveform data using a reliable request-response protocol.
 * It first sends a mode identifier, then the number of quantum bits, followed by
 * the waveform data for each quantum bit with appropriate acknowledgments.
 *
 * @param[in] qubit_count Number of quantum bits to send
 * @param[in] arry_counts Array containing the number of data points for each quantum bit
 * @param[in] qubit Three-dimensional array containing quantum bit waveform data
 * @param[in] ip IP address of the target quantum processing board
 * @param[in] card_id Identifier of the target quantum processing board
 * @param[in] comm MPIQ_Comm structure defining the communication domain
 * @return 0 on successful transmission, -1 on error
 *
 * @note The function uses port 5000 + card_id for communication
 * @attention Each data transmission is followed by an acknowledgment check
 */
int MPIQ_Send(int qubit_count, int *arry_counts, char ***qubit, char *ip, int card_id, MPIQ_Comm comm)
{
    int sock = 0;                  // Socket file descriptor
    struct sockaddr_in serv_addr;  // Server address structure
    char buffer[BUFFERSIZE] = {0}; // Communication buffer

    // Create TCP socket for communication
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0)
    {
        perror("socket creation failed");
        return -1;
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
        return -1;
    }
    // Connect to the quantum processing board
    if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0)
    {
        perror("Failed to connect to server (please check if IP and port are correct)");
        return -1;
    }
    printf("Successfully connected to server (IP: %s, Port: %d)\n", ip, PORT);
    // Send communication mode to initiate the protocol
    char mode[] = "request for send";
    send_all(sock, mode, sizeof(mode), 0);

    // Wait for acknowledgment from server
    while (1)
    {
        ssize_t valread = recv_all(sock, buffer, BUFFERSIZE - 1, 0);
        if (valread < 0) { close(sock); return -1; }
        buffer[BUFFERSIZE - 1] = '\0';
        if (strcmp(buffer, "right") == 0)
            break;
    }
    memset(buffer, 0, BUFFERSIZE);
    // Send number of quantum bits to the server
    qubit_print(qubit, qubit_count, arry_counts);
    char count_str[100];
    sprintf(count_str, "%d", qubit_count);
    send_all(sock, count_str, sizeof(count_str), 0);

    // Wait for acknowledgment
    while (1)
    {
        ssize_t valread = recv_all(sock, buffer, BUFFERSIZE - 1, 0);
        if (valread < 0) { close(sock); return -1; }
        buffer[BUFFERSIZE - 1] = '\0';
        if (strcmp(buffer, "right") == 0)
            break;
    }
    memset(buffer, 0, BUFFERSIZE);
    // BUG FIX (v29->v30): The original code called memset(BUFFERSIZE=65536) on a
    // 100-byte count_str buffer, causing an out-of-bounds write.
    // Changed to use sizeof(count_str) instead.
    memset(count_str, 0, sizeof(count_str));
    // Send quantum bit waveform data for each quantum bit
    for (int i = 0; i < qubit_count; i++)
    {
        // First, send the number of data points for this quantum bit
        sprintf(count_str, "%d", arry_counts[i]);
        send_all(sock, count_str, sizeof(count_str), 0);

        // Wait for acknowledgment
        while (1)
        {
            ssize_t valread = recv_all(sock, buffer, BUFFERSIZE - 1, 0);
            if (valread < 0) { close(sock); return -1; }
            buffer[BUFFERSIZE - 1] = '\0';
            if (strcmp(buffer, "right") == 0)
                break;
        }
        memset(buffer, 0, BUFFERSIZE);
    // BUG FIX (v29->v30): Same issue as above; corrected the zeroing size for count_str.
    memset(count_str, 0, sizeof(count_str));
        // Then, send each waveform data point for this quantum bit
        for (int j = 0; j < arry_counts[i]; j++)
        {
            // Send waveform data (25 bytes per data point)
            send_all(sock, qubit[i][j], 25, 0);

            // Wait for acknowledgment for each data point
            while (1)
            {
                ssize_t valread = recv_all(sock, buffer, BUFFERSIZE - 1, 0);
                if (valread < 0) { close(sock); return -1; }
                buffer[BUFFERSIZE - 1] = '\0';
                if (strcmp(buffer, "right") == 0)
                    break;
            }
            memset(buffer, 0, BUFFERSIZE);
        }
    }

    // Write received quantum bit data to file
    FILE *fp;
    char filename[] = "../data/send_data.txt";

    fp = fopen(filename, "w");
    if (fp == NULL)
    {
        perror("Failed to open file for writing");
        // Continue execution even if file writing fails
    }
    else
    {
        // Write qubit count
        fprintf(fp, "%d\n", qubit_count);

        // Write data point counts for each qubit
        for (int i = 0; i < qubit_count; i++)
        {
            fprintf(fp, "%d ", arry_counts[i]);
        }
        fprintf(fp, "\n");

        // Write the actual quantum bit waveform data
        for (int i = 0; i < qubit_count; i++)
        {
            for (int j = 0; j < arry_counts[i]; j++)
            {
                fprintf(fp, "%s ", qubit[i][j]);
            }
            fprintf(fp, "\n");
        }

        fclose(fp);
    // BUG FIX (v29->v30): The original log message referenced "all_qubits.txt" which did not
    // match the actual filename send_data.txt. Corrected.
    printf("Successfully wrote send data to %s\n", filename);
    }

    // Close the socket connection
    close(sock);

    // Return success
    return 0;
}

/**
 * @file server_test1.c
 * @brief TCP server implementation for quantum processing board communication
 *
 * This module implements a TCP server that communicates with MPIQ clients
 * to handle quantum bit data transmission. It supports three main request types:
 * 1. Result retrieval from quantum processing boards
 * 2. Receiving quantum bit waveform data from classical processes
 * 3. Sending data for gather operations
 *
 * The server binds to a specified IP and port, listens for incoming connections,
 * and processes requests in a continuous loop.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "../MPIQ/MPIQ.h"

/** @def BUFFER_SIZE
 *  @brief Size of buffer for network communication
 */
#define BUFFER_SIZE 65536

/**
 * @brief Main function for the quantum processing board server
 *
 * Initializes and runs the TCP server that handles communication with MPIQ clients.
 * The server processes three types of requests: result retrieval, data reception, and data sending.
 *
 * @param argc Number of command-line arguments
 * @param argv Array of command-line arguments
 * @return 0 on successful execution (though the server runs indefinitely)
 */
int main(int argc, char *argv[])
{
    printf("running...\n");
    char *IP = argv[1];
    int PORT = atoi(argv[2]);
    int server_fd, new_socket;      // Socket file descriptors
    struct sockaddr_in address;     // Server address structure
    int addrlen = sizeof(address);  // Length of address structure
    char buffer[BUFFER_SIZE] = {0}; // Buffer for network communication
    char send_message[] = "right";  // Acknowledgment message
    ssize_t valread;                // Number of bytes read from socket
    char ***qubit = NULL;           // Quantum bit data storage
    char **wave_arry;
    int qubit_count;         // Number of quantum bits
    int *arry_counts = NULL; // Array of waveform data point counts

    // Create a TCP socket
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0)
    {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    // Configure server address information
    address.sin_family = AF_INET;   // IPv4 protocol
    address.sin_port = htons(PORT); // Convert port to network byte order

    // Convert string IP to network byte order and bind
    if (inet_pton(AF_INET, IP, &address.sin_addr) <= 0)
    {
        perror("Invalid IP address");
        exit(EXIT_FAILURE);
    }

    // Bind the socket to the specified IP and port
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0)
    {
        perror("Binding failed (please check if the IP is correct or the port is occupied)");
        exit(EXIT_FAILURE);
    }
    printf("Server bound to IP: %s, Port: %d\n", IP, PORT);

    // Listen for connections (maximum waiting queue length is 5)
    if (listen(server_fd, 5) < 0)
    {
        perror("Listening failed");
        exit(EXIT_FAILURE);
    }
    // Infinite loop to accept and process client connections
    while (1)
    {
        printf("Server is listening for connections...\n");

        // Accept incoming connection
        if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t *)&addrlen)) < 0)
        {
            perror("Failed to accept connection");
            exit(EXIT_FAILURE);
        }

        printf("Connected: IP = %s, Port = %d\n",
               inet_ntoa(address.sin_addr), ntohs(address.sin_port));

        // Receive request type from client
        valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
        buffer[valread] = '\0'; // Use single quote for char literal

        int switch_token = 0;   // Token to determine request type
        char line[BUFFER_SIZE]; // Buffer for file lines

        // Determine request type
        if (strcmp(buffer, "request for result") == 0)
            switch_token = 1; // Result retrieval request
        if (strcmp(buffer, "request for send") == 0)
            switch_token = 2; // Data reception request
        switch (switch_token)
        {
            /**
             * @brief Case 1: Handle result retrieval request
             *
             * This case handles requests for calculation results from quantum processing boards.
             * It reads results from a CSV file and sends them to the client line by line.
             */
        case 1:
        {
            memset(buffer, 0, BUFFER_SIZE);
            send(new_socket, send_message, sizeof(send_message), 0);

            // Wait for client acknowledgment
            while (1)
            {
                valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                buffer[valread] = '\0'; // Use single quote for char literal
                if (strcmp(buffer, "right") == 0)
                    break;
            }

            memset(buffer, 0, BUFFER_SIZE);

            // Open result file for reading
            FILE *result;
            char file[50];
            sprintf(file, "../data/result%d.txt", (atoi(argv[2]) - 5000));
            result = fopen(file, "r");
            if (result == NULL)
            {
                printf("Error opening file.\n");
                close(new_socket); // Close socket before continuing
                continue;          // Skip to next connection
            }

            int times = 0;
            printf("send message\n");

            // Read and send each line of the result file
            while (fgets(line, sizeof(line), result))
            {
                // Remove newline character from line
                line[strcspn(line, "\n")] = '\0';

                // Send the line to client
                send(new_socket, line, strlen(line) + 1, 0);

                // Wait for acknowledgment
                while (1)
                {
                    valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                    buffer[valread] = '\0'; // Use single quote for char literal
                    if (strcmp(buffer, "right") == 0)
                        break;
                }

                // Clear buffers for next iteration
                memset(buffer, 0, BUFFER_SIZE);
                memset(line, 0, BUFFER_SIZE);
                times++;
            }

            fclose(result);

            // Send exit signal to client
            char break_str[] = "exit";
            send(new_socket, break_str, sizeof(break_str), 0);

            // Wait for acknowledgment
            while (1)
            {
                valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                buffer[valread] = '\0'; // Use single quote for char literal
                if (strcmp(buffer, "right") == 0)
                    break;
            }

            memset(buffer, 0, BUFFER_SIZE);
            close(new_socket);
            printf("Message sent already...\n");
            break;
        }
        /**
         * @brief Case 2: Handle data reception request
         *
         * This case receives quantum bit waveform data from MPIQ clients.
         * It first receives the number of quantum bits, then for each quantum bit,
         * it receives the number of waveform data points and the actual data.
         */
        case 2:
        {
            arry_counts = NULL;
            send(new_socket, send_message, strlen(send_message), 0);
            memset(buffer, 0, BUFFER_SIZE);

            // Receive number of quantum bits
            valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
            buffer[valread] = '\0'; // Use single quote for char literal
            printf("quibit number: %s\n", buffer);
            qubit_count = atoi(buffer);

            memset(buffer, 0, BUFFER_SIZE);
            send(new_socket, send_message, strlen(send_message), 0);

            // Receive data for each quantum bit
            for (int times = 0; times < qubit_count; times++)
            {
                // First, receive the length of the waveform array
                valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                buffer[valread] = '\0'; // Use single quote for char literal
                printf("arry number: %s\n", buffer);
                int arry_count = atoi(buffer);

                // Allocate memory for array counts
                arry_counts = (int *)realloc(arry_counts, (times + 1) * sizeof(int));
                arry_counts[times] = arry_count;

                memset(buffer, 0, BUFFER_SIZE);
                send(new_socket, send_message, strlen(send_message), 0);

                // Then, receive the actual waveform data
                qubit = (char ***)realloc(qubit, (times + 1) * sizeof(char **));
                wave_arry = NULL;

                for (int i = 0; i < arry_count; i++)
                {
                    valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                    buffer[valread] = '\0'; // Use single quote for char literal

                    // Allocate memory for waveform data point
                    wave_arry = (char **)realloc(wave_arry, (i + 1) * sizeof(char *));
                    wave_arry[i] = (char *)malloc(strlen(buffer) + 1); // Prevent buffer overflow
                    strcpy(wave_arry[i], buffer);

                    memset(buffer, 0, BUFFER_SIZE);
                    send(new_socket, send_message, strlen(send_message), 0);
                }

                qubit[times] = wave_arry;
            }

            // Print received quantum bit data
            qubit_print(qubit, qubit_count, arry_counts);
            // Write received quantum bit data to file
            FILE *fp;
            char filename[50];
            sprintf(filename, "../data/server_recv_result%d.txt", (atoi(argv[2]) - 5000));

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
                printf("Successfully wrote received data to %s\n", filename);
            }
            close(new_socket);
            break;
        }
        }
    }
    // Close server socket (unreachable in current code, but included for completeness)
    close(server_fd);

    exit(EXIT_SUCCESS);
    // return 0;
}

/**
 * @file server_barrier2.c
 * @brief Barrier server instance 2 for quantum processing board communication
 *
 * This server handles three types of requests from the MPIQ client:
 *   1. "request for result" - Sends computation results back to the client
 *   2. "request for send"   - Receives qubit waveform data sent by MPIQ_Send
 *   3. "request for gather" - Responds to gather requests from MPIQ_Gather
 *
 * After receiving data, it performs a barrier synchronization and writes
 * the results to a file for verification.
 *
 * This server listens on IP 127.0.0.1, Port 5002.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "../MPIQ/MPIQ.h"
#include <time.h>

#define BUFFER_SIZE 65536
#define IP "127.0.0.1"
#define PORT 5002
int main(int argc, char *argv[])
{
    int server_fd, new_socket;
    struct sockaddr_in address;
    int addrlen = sizeof(address);
    char buffer[BUFFER_SIZE] = {0};
    char send_message[] = "right";
    ssize_t valread;
    char ***qubit = NULL;
    char **wave_arry;
    int qubit_count;
    int *arry_counts;

    MPIQ_Comm comm;     // comm as a parameter to the barrier function.
    struct timespec ts; // Store high-precision time

    // Create a TCP socket
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0)
    {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }
    // Configure server address information
    address.sin_family = AF_INET;   // IPv4
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
    while (1)
    {
        printf("Server is listening for connections...\n");
        if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t *)&addrlen)) < 0)
        {
            perror("Failed to accept connection");
            exit(EXIT_FAILURE);
        }
        printf("Connected: IP = %s, Port = %d\n",
               inet_ntoa(address.sin_addr), ntohs(address.sin_port));
        valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
        buffer[valread] = '\0';
        int switch_token = 0;
        char line[BUFFER_SIZE];
        if (strcmp(buffer, "request for result") == 0)
            switch_token = 1;
        if (strcmp(buffer, "request for send") == 0)
            switch_token = 2;
        if (strcmp(buffer, "request for gather") == 0)
            switch_token = 3;
        switch (switch_token)
        {
        // ​​The purpose of  case 1 is to send the information calculate by card.
        case 1:
            memset(buffer, 0, BUFFER_SIZE);
            send(new_socket, send_message, sizeof(send_message), 0);
            while (1)
            {
                valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                buffer[valread] = '\0';
                if (strcmp(buffer, "right") == 0)
                    break;
            }
            memset(buffer, 0, BUFFER_SIZE);
            // send result
            FILE *result;
            result = fopen("../data/result2.txt", "r");
            if (result == NULL)
            {
                printf("Error opening file.\n");
                continue;
            }
            int times = 0;
            printf("send message\n");
            while (fgets(line, sizeof(line), result))
            {
                // Send the corresponding information
                line[strcspn(line, "\n")] = '\0';
                // printf("send_message%d is:%s\n", times, line);
                send(new_socket, line, strlen(line) + 1, 0);
                while (1)
                {
                    valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                    buffer[valread] = '\0';
                    if (strcmp(buffer, "right") == 0)
                        break;
                }
                memset(buffer, 0, BUFFER_SIZE);
                memset(line, 0, BUFFER_SIZE);
                times++;
            }
            fclose(result);
            char break_str[] = "exit";
            send(new_socket, break_str, sizeof(break_str), 0);
            while (1)
            {
                valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                buffer[valread] = '\0';
                if (strcmp(buffer, "right") == 0)
                    break;
            }
            memset(buffer, 0, BUFFER_SIZE);
            close(new_socket);
            printf("Message sent already...\n");
            break;
        // ​​The purpose of  case 2 is to receive the information sent by MPIQ_send.
        case 2:
            arry_counts = NULL;
            send(new_socket, send_message, strlen(send_message), 0);
            memset(buffer, 0, BUFFER_SIZE);
            // recive q_count
            valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
            buffer[valread] = '\0';
            printf("quibit number: %s\n", buffer);
            qubit_count = atoi(buffer);
            memset(buffer, 0, BUFFER_SIZE);
            send(new_socket, send_message, strlen(send_message), 0);
            // recive arry_counts and qubit
            for (int times = 0; times < qubit_count; times++)
            {
                // First, receive the length of the array containing the quantum bit waveform data and store it.
                valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                buffer[valread] = '\0';
                printf("arry number: %s\n", buffer);
                int arry_count = atoi(buffer);
                arry_counts = (int *)realloc(arry_counts, (times + 1) * sizeof(int));
                arry_counts[times] = arry_count;
                memset(buffer, 0, BUFFER_SIZE);
                send(new_socket, send_message, strlen(send_message), 0);
                // Then, obtain the quantum bit waveform data.
                qubit = (char ***)realloc(qubit, (times + 1) * sizeof(char **));
                wave_arry = NULL;
                for (int i = 0; i < arry_count; i++)
                {
                    valread = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
                    buffer[valread] = '\0';
                    wave_arry = (char **)realloc(wave_arry, (i + 1) * sizeof(char *));
                    wave_arry[i] = (char *)malloc(25 * sizeof(char));
                    strcpy(wave_arry[i], buffer);
                    memset(buffer, 0, BUFFER_SIZE);
                    send(new_socket, send_message, strlen(send_message), 0);
                }
                qubit[times] = wave_arry;
            }

            //
            printf("Arrie at the barrier\n");
            MPIQ_Barrier(comm, 1);
            clock_gettime(CLOCK_REALTIME, &ts);
            printf("Current time ：%lds + %ldns\n", ts.tv_sec, ts.tv_nsec);

            qubit_print(qubit, qubit_count, arry_counts);
            // Write received quantum bit data to file
            FILE *fp;
            char filename[50];
            sprintf(filename, "../data/server_barrier_result2.txt");

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
        case 3:
            send(new_socket, send_message, strlen(send_message), 0);
            memset(buffer, 0, BUFFER_SIZE);
            while (1)
            {
                valread = recv(new_socket, buffer, BUFFERSIZE - 1, 0);
                buffer[valread] = '\0';
                if (strcmp(buffer, "right"))
                    break;
            }
            memset(buffer, 0, BUFFER_SIZE);
            char count_str[100];
            sprintf(count_str, "%d", qubit_count);
            send(new_socket, count_str, sizeof(count_str), 0);
            while (1)
            {
                ssize_t valread = recv(new_socket, buffer, BUFFERSIZE - 1, 0);
                buffer[valread] = '\0';
                if (strcmp(buffer, "right"))
                    break;
            }
            memset(buffer, 0, BUFFERSIZE);
            char strs[100];
            for (int i = 0; i < qubit_count; i++)
            {
                for (int j = 0; j < 6; j++)
                {
                    sprintf(strs, "%s", qubit[i][j]);
                    send(new_socket, strs, sizeof(strs), 0);
                    while (1)
                    {
                        ssize_t valread = recv(new_socket, buffer, BUFFERSIZE - 1, 0);
                        buffer[valread] = '\0';
                        if (strcmp(buffer, "right"))
                            break;
                    }
                    memset(strs, 0, 100);
                    memset(buffer, 0, BUFFERSIZE);
                }
            }
            close(new_socket);
            break;
        }
    }
    close(server_fd);
}

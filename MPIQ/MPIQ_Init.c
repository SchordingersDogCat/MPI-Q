/**
 * @file MPIQ_init.c
 * @brief MPIQ communication domain initialization module for quantum processing systems
 *
 * This module implements the MPIQ_Init function, which is responsible for
 * initializing the MPIQ communication domain that connects classical processes
 * with quantum processing hardware. It serves as the foundation for both classical-classical
 * and classical-quantum communications in the MPIQ library.
 *
 * Key functionalities include:
 * - Parsing configuration files to identify quantum hardware resources
 * - Managing IP addresses and board card mappings
 * - Initializing MPI for classical-classical communications when requested
 * - Setting up the communication domain structure for all subsequent operations
 * - Handling configuration errors and providing diagnostic messages
 *
 * This module is part of the MPIQ library, which extends MPI functionality
 * for quantum-classical hybrid computing applications.
 */

#include "MPIQ.h"
#include <mpi.h>

/**
 * @brief Internal implementation of MPIQ communication domain initialization
 *
 * @param[in] argc Argument count passed from main
 * @param[in] argv Argument vector passed from main
 * @param[out] rank Sequence number of the classical process within the communication domain
 * @param[in] comm_token Communication category identifier ("CC" for classical-to-classical)
 * @param[in] qubit_wave Custom MPI data type for qubit wave operations
 * @param[in] config_path Path to the configuration file (IP addresses and card counts)
 * @return MPIQ_Comm structure representing the initialized communication domain
 *
 * @note For classical-to-quantum communication, comm_token should be NULL
 * @warning If the configuration file cannot be opened, the function will terminate with EXIT_FAILURE
 * @warning The function may return an incomplete communication domain if file parsing errors occur
 */
MPIQ_Comm MPIQ_Init_ex(int *argc, char ***argv, int *rank, char *comm_token, MPI_Datatype *qubit_wave, const char *config_path)
{
    // Open the configuration file containing IP addresses and card counts
    FILE *send_file = fopen(config_path, "r");
    if (!send_file)
    {
        fprintf(stderr, "Failed to open config file: %s\n", config_path);
        exit(EXIT_FAILURE);
    }

    // Initialize communication structure
    MPIQ_Comm temp;
    // temp.custom_comm = MPI_COMM_WORLD;  // Commented out, not currently used
    temp.ip_addr = NULL;       // Array to store quantum board IP addresses
    temp.card_id_count = NULL; // Array to store number of cards per IP
    temp.count = 0;            // Counter for IP addresses
    temp.size = 0;             // Size of the MPI communicator (initialized later)
    char line[256];            // Buffer for reading lines from configuration file
    char *token;               // Token pointer for string parsing
    int continue_token;        // Flag to continue to next iteration

    // Read each line from the configuration file
    while (fgets(line, sizeof(line), send_file))
    {
        continue_token = 0;

        // Remove newline character if it exists
        line[strcspn(line, "\n")] = '\0';

        // Extract IP part from the line
        token = strtok(line, ",");
        if (token == NULL)
        {
            printf("File content format error, missing IP address\n");
            return temp;
        }

        temp.count++;

        // Check if IP already exists in the list
        for (int i = 0; i < temp.count - 1; i++)
        {
            if (strcmp(temp.ip_addr[i], token) == 0)
            {
                // Extract card count for existing IP
                token = strtok(NULL, ",");
                if (token == NULL)
                {
                    printf("File content format error, missing number\n");
                    return temp;
                }
                temp.card_id_count[i]++;
                continue_token = 1;
                break;
            }
        }

        if (continue_token)
        {
            continue;
        }

        // Allocate memory for new IP address
        temp.ip_addr = (char **)realloc(temp.ip_addr, temp.count * sizeof(char *));
        temp.ip_addr[temp.count - 1] = NULL;
        temp.ip_addr[temp.count - 1] = (char *)realloc(temp.ip_addr[temp.count - 1], 20);
        strcpy(temp.ip_addr[temp.count - 1], token);

        // Extract card count part
        token = strtok(NULL, ",");
        if (token == NULL)
        {
            printf("File content format error, missing number\n");
            return temp;
        }

        // Allocate memory for card count
        temp.card_id_count = (int *)realloc(temp.card_id_count, temp.count * sizeof(int));
        temp.card_id_count[temp.count - 1] = atoi(token);
    }

    // Close the configuration file
    fclose(send_file); // Use fclose for file pointers opened with fopen
    // Initialize MPI if classical-classical communication is requested
    if (comm_token != NULL && strcmp(comm_token, "CC") == 0)
    {
        MPI_Init(argc, argv);
        temp.mpi_comm = MPI_COMM_WORLD;
        MPI_Comm_rank(temp.mpi_comm, rank);
        MPI_Comm_size(temp.mpi_comm, &(temp.size));
    }

    // Return the initialized communication domain
    return temp;
}

/**
 * @brief Initialize the MPIQ communication domain (backward-compatible wrapper)
 *
 * This is a convenience wrapper that calls MPIQ_Init_ex with the default
 * configuration file path "../test/all_ip.conf". For new code, prefer using
 * MPIQ_Init_ex to specify the config path explicitly.
 */
MPIQ_Comm MPIQ_Init(int *argc, char ***argv, int *rank, char *comm_token, MPI_Datatype *qubit_wave)
{
    return MPIQ_Init_ex(argc, argv, rank, comm_token, qubit_wave, "../test/all_ip.conf");
}
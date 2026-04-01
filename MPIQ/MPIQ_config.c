/**
 * @file MPIQ_config.c
 * @brief MPIQ configuration parsing module for quantum processing systems
 *
 * This module implements configuration parsing utilities for the MPIQ library,
 * focusing on processing JSON configuration files that define quantum bit properties
 * and hardware mappings. It provides functions for reading configuration files,
 * parsing JSON data, and organizing quantum bit configurations according to their
 * physical hardware locations.
 *
 * Key functionalities include:
 * - Reading configuration files into memory
 * - Finding IP address indices in lookup tables
 * - Parsing JSON configuration for quantum bits
 * - Organizing quantum bit configurations by IP address and card ID
 * - Managing memory for configuration data structures
 *
 * This module is part of the MPIQ library, which extends MPI functionality
 * for quantum-classical hybrid computing applications.
 */

#include "MPIQ.h"

/**
 * @brief Read file content into a dynamically allocated string
 *
 * This function reads the entire content of a file into memory and returns
 * it as a null-terminated string. It is primarily used to read JSON configuration
 * files for quantum bit hardware mapping.
 *
 * @param[in] filename Path to the file to be read
 * @return Dynamically allocated string containing file content, or NULL on failure
 *
 * @warning The caller is responsible for freeing the returned memory
 */
char *read_config(const char *filename)
{
    // Open file in binary read mode
    FILE *fp = fopen(filename, "rb");
    if (!fp)
    {
        // File opening failed, return NULL
        return NULL;
    }

    // Get file size by seeking to end and measuring position
    fseek(fp, 0, SEEK_END);
    long length = ftell(fp);
    fseek(fp, 0, SEEK_SET); // Reset file pointer to beginning

    // Allocate memory for file content plus null terminator
    char *data = (char *)malloc(length + 1);
    if (data)
    {
        // Read file content into memory
        fread(data, 1, length, fp);
        data[length] = '\0'; // Add null terminator to make it a proper string
    }

    // Close file handle
    fclose(fp);

    // Return file content (or NULL if memory allocation failed)
    return data;
}

/**
 * @brief Find the index of an IP address in a lookup table
 *
 * This function searches for a specific IP address string in a fixed-size array
 * of IP addresses. It is used to map IP addresses to integer indices for more
 * efficient array indexing operations.
 *
 * @param[in] list Array of IP address strings to search
 * @param[in] strings The IP address string to find
 * @return Index of the IP address in the list if found, or -1 if not found
 *
 * @note The function searches up to 10 elements in the list
 * @note Returns -1 as a sentinel value when the IP is not found
 */
int find_index(char (*list)[14], char *strings)
{
    // Iterate through the IP address list (maximum 10 entries)
    for (int i = 0; i < 10; i++)
    {
        // Compare current IP address with the target
        if (strcmp(list[i], strings) == 0)
            return i; // Return index if match found
    }

    // Return -1 if IP not found
    return -1;
}

/**
 * @brief Parse qubit configuration data from a JSON file
 *
 * This function reads and parses a JSON configuration file containing qubit
 * hardware mapping information. It organizes the configuration data into a
 * hierarchical structure based on IP addresses, card IDs, and channel IDs.
 *
 * @param[in] json_file Path to the JSON configuration file
 * @param[out] ip_card_configs Triple-pointer to store the parsed configuration hierarchy
 * @param[out] card_count Double-pointer to store qubit counts per card
 * @return Pointer to the parsed configuration hierarchy, or NULL on error
 *
 * @warning The function allocates significant memory that must be properly freed
 * @attention Uses fixed-size arrays with maximum of 10 IP addresses and 10 cards per IP
 * @note Depends on the cJSON library for JSON parsing
 */
QubitConfig ***parse_qubit_configs_v2(const char *json_file,
                                      QubitConfig ***ip_card_configs, int ***card_count)
{
    // Initialize output parameters
    int **temp_card_count = NULL;

    // Allocate memory for card count tracking (max 10 IPs, 10 cards per IP)
    for (int i = 0; i < 10; i++)
    {
        // Reallocate memory for the IP dimension
        temp_card_count = (int **)realloc(temp_card_count, (i + 1) * sizeof(int *));

        // Allocate memory for card dimension
        temp_card_count[i] = (int *)malloc(10 * sizeof(int));

        // Initialize all card counts to zero
        for (int j = 0; j < 10; j++)
        {
            temp_card_count[i][j] = 0;
        }
    }
    // Step 1: Allocate first dimension (IP index)
    ip_card_configs = (QubitConfig ***)malloc(10 * sizeof(QubitConfig **));

    // Step 2: Allocate second dimension (card ID for each IP)
    for (int i = 0; i < 10; i++)
    {
        // Allocate and initialize to NULL for each card under this IP
        ip_card_configs[i] = (QubitConfig **)calloc(10, sizeof(QubitConfig *));

        // Initially, the configuration array for each card is NULL (expanded with realloc later)
        for (int j = 0; j < 10; j++)
        {
            ip_card_configs[i][j] = NULL;
        }
    }
    // Set up a mapping index for IP addresses
    char ip_index[10][14]; // Array to map IP addresses to numeric indices

    // Initialize all bytes to '0' to create a default state
    memset(ip_index, '0', 10 * 14);

    // Ensure each IP string is properly null-terminated
    for (int i = 0; i < 10; i++)
    {
        ip_index[i][14 - 1] = '\0'; // Set the last byte to '\0' to ensure the string is complete
    }

    // Read configuration file
    printf("Start reading configuration file...\n");
    char *json_data = read_config(json_file);
    if (!json_data)
    {
        perror("Failed to open configuration file");
        // Free previously allocated memory before returning
        for (int i = 0; i < 10; i++)
        {
            free(temp_card_count[i]);
        }
        free(temp_card_count);
        free(ip_card_configs);
        return NULL;
    }

    // Parse JSON data
    cJSON *root = cJSON_Parse(json_data);
    free(json_data); // Free file content after parsing

    if (!root)
    {
        fprintf(stderr, "JSON parsing failed: %s\n", cJSON_GetErrorPtr());
        // Free previously allocated memory before returning
        for (int i = 0; i < 10; i++)
        {
            free(temp_card_count[i]);
        }
        free(temp_card_count);
        free(ip_card_configs);
        return NULL;
    }

    // Generate index to map IP values to indices
    int index_num = -1; // Current index for new IP addresses

    // Traverse and parse each qubit configuration in the JSON array
    cJSON *current_qubit = NULL;
    cJSON_ArrayForEach(current_qubit, root)
    {
        // Get the name (key name) of the current qubit
        const char *key = current_qubit->string;
        if (!key)
            key = "unknown_qubit"; // Default name if key is missing

        // Parse a single qubit configuration
        QubitConfig cfg;                              // Structure to hold current qubit configuration
        strncpy(cfg.name, key, sizeof(cfg.name) - 1); // Copy qubit name

        // Parse each field from JSON
        // Parse IP address
        cJSON *ip = cJSON_GetObjectItemCaseSensitive(current_qubit, "ip");
        if (cJSON_IsString(ip) && (ip->valuestring != NULL))
        {
            strncpy(cfg.ip, ip->valuestring, sizeof(cfg.ip) - 1);
        }

        // Parse card ID
        cJSON *card_id = cJSON_GetObjectItemCaseSensitive(current_qubit, "card_id");
        if (cJSON_IsNumber(card_id))
        {
            cfg.card_id = card_id->valueint;
        }

        // Parse channel ID
        cJSON *channel_id = cJSON_GetObjectItemCaseSensitive(current_qubit, "channel_id");
        if (cJSON_IsNumber(channel_id))
        {
            cfg.channel_id = channel_id->valueint;
        }

        cJSON *waveshape = cJSON_GetObjectItemCaseSensitive(current_qubit, "waveshape");
        if (cJSON_IsNumber(waveshape))
        {
            cfg.waveshape = waveshape->valueint;
        }

        cJSON *freq_Hz = cJSON_GetObjectItemCaseSensitive(current_qubit, "freq_Hz");
        if (cJSON_IsNumber(freq_Hz))
        {
            cfg.freq_Hz = freq_Hz->valuedouble;
        }

        cJSON *ampl = cJSON_GetObjectItemCaseSensitive(current_qubit, "ampl");
        if (cJSON_IsNumber(ampl))
        {
            cfg.ampl = ampl->valuedouble;
        }

        cJSON *phase_rad = cJSON_GetObjectItemCaseSensitive(current_qubit, "phase_rad");
        if (cJSON_IsNumber(phase_rad))
        {
            cfg.phase_rad = phase_rad->valuedouble;
        }

        cJSON *dc_offset = cJSON_GetObjectItemCaseSensitive(current_qubit, "dc_offset");
        if (cJSON_IsNumber(dc_offset))
        {
            cfg.dc_offset = dc_offset->valuedouble;
        }

        cJSON *sample_rate_Hz = cJSON_GetObjectItemCaseSensitive(current_qubit, "sample_rate_Hz");
        if (cJSON_IsNumber(sample_rate_Hz))
        {
            cfg.sample_rate_Hz = sample_rate_Hz->valuedouble;
        }
        // Get the index of the current IP address in our mapping
        int real_index = find_index(ip_index, cfg.ip);
        int id = cfg.card_id; // Local copy of card ID
        // If the IP address already exists in our mapping
        if (real_index >= 0)
        {
            // Increment qubit count for this card
            temp_card_count[real_index][id]++;

            // Allocate more memory for the qubit configuration
            ip_card_configs[real_index][id] = (QubitConfig *)realloc(
                ip_card_configs[real_index][id],
                temp_card_count[real_index][id] * sizeof(QubitConfig));

            // Copy the configuration to the allocated memory
            ip_card_configs[real_index][id][temp_card_count[real_index][id] - 1] = cfg;

            // Debug output - note: this uses index_num which may not match real_index
            printf("%s\n", ip_card_configs[real_index][id][temp_card_count[real_index][id] - 1].name);
            printf("%d %d %d\n", real_index, id, temp_card_count[real_index][id] - 1);
        }
        // If this is a new IP address
        else
        {
            // Increment index counter for new IP
            index_num++;

            // Add IP to our mapping
            strcpy(ip_index[index_num], cfg.ip);

            // Initialize count and allocate memory for this new IP and card
            temp_card_count[index_num][cfg.card_id]++;
            ip_card_configs[index_num][cfg.card_id] = (QubitConfig *)realloc(
                ip_card_configs[index_num][cfg.card_id],
                temp_card_count[index_num][cfg.card_id] * sizeof(QubitConfig));

            // Copy configuration
            ip_card_configs[index_num][cfg.card_id][temp_card_count[index_num][cfg.card_id] - 1] = cfg;

            // Debug output
            printf("%s\n", ip_card_configs[index_num][cfg.card_id][temp_card_count[index_num][cfg.card_id] - 1].name);
            printf("%d %d %d\n", index_num, cfg.card_id, temp_card_count[index_num][cfg.card_id] - 1);
        }
    }

    // Set output parameter for card counts
    *card_count = temp_card_count;

    // Clean up JSON parser object
    cJSON_Delete(root);

    // Return the parsed configuration hierarchy
    return ip_card_configs;
}
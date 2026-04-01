/**
 * @file MPIQ_qasmtowave.c
 * @brief QASM-to-pulse-waveform conversion module (Python bridge + IQ modulation)
 *
 * This module uses the Python C API to call pulse_converter_removetranspile.py,
 * parsing QASM quantum circuit files into baseband envelope signals, then applying
 * IQ modulation to generate real-valued pulse waveform sequences for quantum
 * measurement and control boards.
 *
 * Key functionalities:
 *   - c99_complex_to_string   : Convert C99 complex to string (format "real+imagj")
 *   - double_to_string        : Convert double value to string (6 decimal places)
 *   - parse_python_complex    : Extract real and imaginary parts from a Python object
 *   - complex_multiply_real_part: Compute real part of two complex numbers' product (for IQ modulation)
 *   - qasm_to_pulse_waveforms : Full pipeline: QASM -> Python parse -> IQ modulate -> char*** output
 *   - qubit_print_modulated_waveforms: Print modulated waveform summary (for debugging)
 *
 * Modulation parameters (currently hardcoded):
 *   - Sampling rate: 4.5 GS/s (dt ~ 222 ps)
 *   - Carrier frequency: 5.04 GHz
 *
 * This module is part of the MPIQ library, supporting pulse generation in
 * quantum-classical hybrid computing.
 *
 * @note This module depends on Python 3.11 runtime and pulse_converter_removetranspile.py.
 * @warning The caller must free the memory returned by qasm_to_pulse_waveforms.
 */
#include "/usr/include/python3.11/Python.h"
#include <complex.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#define M_PI 3.14159265358979323846

/**
 * @brief Convert a C99 complex number to a Python-style string representation
 *
 * Positive imaginary part format: "real+imagj"; negative imaginary part format: "realImagj"
 * (imag itself contains the negative sign)
 *
 * @param[in]  c    C99 double _Complex number
 * @param[out] str  Pointer to output string; allocated internally via malloc, caller must free()
 */
void c99_complex_to_string(double _Complex c, char **str)
{
    double real = creal(c); // Extract real part
    double imag = cimag(c); // Extract imaginary part

    if (imag >= 0)
    {
        int str_len = snprintf(NULL, 0, "%.6f+%.6fj", real, imag);
        *str = (char *)malloc((str_len + 1) * sizeof(char));
        snprintf(*str, str_len + 1, "%.6f+%.6fj", real, imag);
    }
    else
    {
        int str_len = snprintf(NULL, 0, "%.6f%.6fj", real, imag);
        *str = (char *)malloc((str_len + 1) * sizeof(char));
        snprintf(*str, str_len + 1, "%.6f%.6fj", real, imag);
    }
}

/**
 * @brief Convert a double value to a string with 6 decimal places
 *
 * @param[in]  value  The double value to convert
 * @param[out] str    Pointer to output string; allocated internally via malloc, caller must free()
 */
void double_to_string(double value, char **str)
{
    int str_len = snprintf(NULL, 0, "%.6f", value);
    *str = (char *)malloc((str_len + 1) * sizeof(char));
    snprintf(*str, str_len + 1, "%.6f", value);
}

/**
 * @brief Extract real and imaginary parts from a Python object
 *
 * Supports three Python object types: complex, float, int
 *
 * @param[in]  complex_obj  Python object (PyObject*)
 * @param[out] real         Real part output
 * @param[out] imag         Imaginary part output (0.0 for float/int)
 * @return 1 if parsing succeeded, 0 if the type is not supported
 */
int parse_python_complex(PyObject *complex_obj, double *real, double *imag)
{
    if (PyComplex_Check(complex_obj))
    {
        *real = PyComplex_RealAsDouble(complex_obj);
        *imag = PyComplex_ImagAsDouble(complex_obj);
        return 1;
    }
    else if (PyFloat_Check(complex_obj))
    {
        *real = PyFloat_AsDouble(complex_obj);
        *imag = 0.0;
        return 1;
    }
    else if (PyLong_Check(complex_obj))
    {
        *real = (double)PyLong_AsLong(complex_obj);
        *imag = 0.0;
        return 1;
    }
    return 0;
}

/**
 * @brief Compute the real part of the product of two complex numbers (for IQ modulation)
 *
 * IQ modulation formula: (a+bi)*(c+di) = (ac-bd) + (ad+bc)i
 * This function returns only the real part: ac - bd
 *
 * @param[in] envelope_real  Baseband envelope real part a
 * @param[in] envelope_imag  Baseband envelope imaginary part b
 * @param[in] carrier_real   Carrier signal real part c
 * @param[in] carrier_imag   Carrier signal imaginary part d
 * @return Real part of the product: a*c - b*d
 */
double complex_multiply_real_part(double envelope_real, double envelope_imag,
                                  double carrier_real, double carrier_imag)
{
    // Complex multiplication: (a+bi)*(c+di) = (ac - bd) + (ad + bc)i
    // Only the real part is needed: ac - bd
    return envelope_real * carrier_real - envelope_imag * carrier_imag;
}

/**
 * @brief Convert a QASM file to pulse waveform arrays (full pipeline)
 *
 * Pipeline:
 *   1. Initialize the Python interpreter and import the pulse_converter_removetranspile module
 *   2. Call generate_pulses_from_qasm() to obtain baseband envelope dictionaries
 *   3. Apply IQ modulation to each qubit's baseband envelope, generating real waveform sequences
 *   4. Encode waveform sequences as strings, organizing them into a char*** structure
 *   5. Write all waveform data to ../data/all_qubits.txt
 *
 * @param[out] q_count    Number of qubits
 * @param[out] a_counts   Array of waveform sample counts per qubit (caller must free)
 * @param[in]  file       Input QASM file path (relative to the MPIQ directory)
 * @return Three-dimensional character array qubit[qubit_index][sample_index]; caller must free
 *
 * @note Modulation parameters are currently hardcoded: sampling rate 4.5 GS/s, carrier frequency 5.04 GHz
 * @warning The caller must free the returned memory after use
 */
char ***qasm_to_pulse_waveforms(int *q_count, int **a_counts, char *file)
{
    // Set up a dynamic 2D char array to prepare for receiving data
    char **wave_arry;
    char ***qubit = NULL;
    int qubit_count = 0;
    int *arry_counts = NULL;

    // Initialize the Python interpreter
    Py_Initialize();
    if (!Py_IsInitialized())
    {
        printf("Python initialization failed\n");
        return NULL;
    }

    // Before importing the Python module, first add the directory where the module is located to sys.path
    // Get the sys module
    PyObject *sys_module = PyImport_ImportModule("sys");
    if (!sys_module)
    {
        PyErr_Print();
        Py_Finalize();
        return NULL;
    }

    // Get sys.path
    PyObject *sys_path = PyObject_GetAttrString(sys_module, "path");
    if (!sys_path)
    {
        PyErr_Print();
        Py_DECREF(sys_module);
        Py_Finalize();
        return NULL;
    }

    // Add the demo directory (where pulse_converter.py resides) to sys.path
    const char *module_dir = "../demo";
    PyObject *path_obj = PyUnicode_FromString(module_dir);
    if (!path_obj)
    {
        PyErr_Print();
        Py_DECREF(sys_path);
        Py_DECREF(sys_module);
        Py_Finalize();
        return NULL;
    }

    // Append the path to sys.path list
    if (PyList_Append(sys_path, path_obj) != 0)
    {
        PyErr_Print();
        Py_DECREF(path_obj);
        Py_DECREF(sys_path);
        Py_DECREF(sys_module);
        Py_Finalize();
        return NULL;
    }

    // Release temporary path objects
    Py_DECREF(path_obj);
    Py_DECREF(sys_path);
    Py_DECREF(sys_module);

    // Import the pulse converter Python module
    PyObject *pModule = PyImport_ImportModule("pulse_converter_removetranspile");
    if (!pModule)
    {
        PyErr_Print();
        Py_Finalize();
        return NULL;
    }

    // Get the generate_pulses_from_qasm function from the module
    PyObject *pFunc = PyObject_GetAttrString(pModule, "generate_pulses_from_qasm");
    if (!pFunc || !PyCallable_Check(pFunc))
    {
        PyErr_Print();
        Py_DECREF(pModule);
        Py_Finalize();
        return NULL;
    }

    // Build function arguments: arg1 = qasm file path (str), arg2 = True (bool flag)
    PyObject *arg1 = PyUnicode_FromString(file);
    PyObject *arg2 = Py_True;
    Py_INCREF(arg2);
    if (!arg1)
    {
        PyErr_Print();
        Py_DECREF(arg2);
        goto cleanup;
    }

    // Pack arguments into a tuple (length 2)
    PyObject *args = PyTuple_Pack(2, arg1, arg2);
    if (!args)
    {
        PyErr_Print();
        Py_DECREF(arg2);
        goto cleanup;
    }

    // Call the function; expected return value is a dict mapping qubit index -> waveform list
    PyObject *p_arrys = PyObject_CallObject(pFunc, args);
    Py_DECREF(args);
    Py_DECREF(arg1);
    Py_DECREF(arg2);
    Py_DECREF(pFunc);
    if (!p_arrys || !PyDict_Check(p_arrys))
    {
        PyErr_Print();
        Py_DECREF(pModule);
        Py_Finalize();
        return NULL;
    }

    printf("=== Extracting Baseband Envelope for IQ Modulation ===\n");
    printf("Returned object type: %s\n", Py_TYPE(p_arrys)->tp_name);

    PyObject *baseband_dict = NULL;

    // If the returned object is not a dict, try to handle list or unsupported types
    if (!PyDict_Check(p_arrys))
    {
        printf("Warning: Returned object is not a dictionary, trying to handle...\n");

        if (PyList_Check(p_arrys))
        {
            printf("Returned object is a list, wrapping into dummy dictionary\n");
            PyObject *temp_dict = PyDict_New();
            PyDict_SetItemString(temp_dict, "0", p_arrys);
            baseband_dict = temp_dict;
        }
        else
        {
            printf("Error: Unsupported return type: %s\n", Py_TYPE(p_arrys)->tp_name);
            Py_DECREF(p_arrys);
            Py_DECREF(pModule);
            Py_Finalize();
            return NULL;
        }
    }
    else
    {
        // Print all available keys in the returned dict for debugging
        PyObject *keys = PyDict_Keys(p_arrys);
        printf("Available keys in result dict (%zd total):\n", PyList_Size(keys));
        for (Py_ssize_t i = 0; i < PyList_Size(keys); i++)
        {
            PyObject *key = PyList_GetItem(keys, i);
            PyObject *key_str = PyObject_Str(key);
            if (key_str)
            {
                printf("  key %zd: %s\n", i, PyUnicode_AsUTF8(key_str));
                Py_DECREF(key_str);
            }
        }
        Py_DECREF(keys);

        // Try known key names to locate the baseband waveform data
        const char *possible_keys[] = {
            "combined_pulses", "gate_pulses", "pulses",
            "waveforms", "q0", "q1", "qubit_0", "qubit_1", NULL};

        baseband_dict = NULL;
        for (int i = 0; possible_keys[i] != NULL; i++)
        {
            PyObject *temp_dict = PyDict_GetItemString(p_arrys, possible_keys[i]);
            if (temp_dict)
            {
                printf("Found key '%s'\n", possible_keys[i]);

                if (PyDict_Check(temp_dict))
                {
                    baseband_dict = temp_dict;
                    printf("Using '%s' as baseband data dict\n", possible_keys[i]);
                    break;
                }
                else if (PyList_Check(temp_dict))
                {
                    // Wrap list into a single-entry dict for uniform processing
                    printf("Wrapping list-format '%s' into dict\n", possible_keys[i]);
                    baseband_dict = PyDict_New();
                    PyDict_SetItemString(baseband_dict, "0", temp_dict);
                    break;
                }
            }
        }

        // If no known key found, try using the entire dict if all values are lists
        if (!baseband_dict)
        {
            printf("Attempting to use the entire result dict as baseband data\n");

            int all_values_are_lists = 1;
            PyObject *key, *value;
            Py_ssize_t pos = 0;

            while (PyDict_Next(p_arrys, &pos, &key, &value))
            {
                if (!PyList_Check(value))
                {
                    // Try converting numpy array to list
                    PyObject *array_list = PyObject_CallMethod(value, "tolist", NULL);
                    if (array_list && PyList_Check(array_list))
                    {
                        Py_DECREF(array_list);
                    }
                    else
                    {
                        if (array_list)
                            Py_DECREF(array_list);
                        all_values_are_lists = 0;
                        break;
                    }
                }
            }

            if (all_values_are_lists)
            {
                baseband_dict = p_arrys;
                Py_INCREF(baseband_dict); // Increment ref count since we're reusing p_arrys
                printf("Using entire result dict as baseband data\n");
            }
        }
    }

    if (!baseband_dict)
    {
        printf("Error: No baseband pulse data found under any known key\n");

        // Create synthetic test data for debugging purposes
        printf("Creating test data for debugging...\n");
        baseband_dict = PyDict_New();
        PyObject *test_waveform = PyList_New(50);

        for (int i = 0; i < 50; i++)
        {
            double t = i * 0.1;
            double real = cos(t);
            double imag = sin(t);
            PyObject *complex_val = PyComplex_FromDoubles(real, imag);
            PyList_SetItem(test_waveform, i, complex_val);
        }

        PyDict_SetItemString(baseband_dict, "0", test_waveform);
        Py_DECREF(test_waveform);

        printf("Created 50 test samples for qubit 0\n");
    }

    // IQ modulation parameters (currently hardcoded)
    double dt = 1.0 / 4.5e9;      // Sampling period ~222ps (4.5 GS/s sampling rate)
    double carrier_freq = 5.04e9; // Carrier frequency: 5.04 GHz

    printf("Modulation parameters: dt=%.3e s, carrier_freq=%.3e Hz\n", dt, carrier_freq);

    // Traverse the baseband dict; each entry: qubit_index -> list of complex envelope samples
    PyObject *pKey, *pValue;
    Py_ssize_t pos = 0;

    printf("Found baseband dictionary with %zd items\n", PyDict_Size(baseband_dict));

    while (PyDict_Next(baseband_dict, &pos, &pKey, &pValue))
    {
        // Ensure the value is a Python list; try numpy tolist() if not
        if (!PyList_Check(pValue))
        {
            PyObject *array_list = PyObject_CallMethod(pValue, "tolist", NULL);
            if (array_list && PyList_Check(array_list))
            {
                pValue = array_list;
            }
            else
            {
                printf("Warning: Value for key is not a list or convertible array\n");
                if (array_list)
                    Py_DECREF(array_list);
                continue;
            }
        }

        // Parse qubit index from the dict key (int or string)
        long qubit_index;
        if (PyLong_Check(pKey))
        {
            qubit_index = PyLong_AsLong(pKey);
        }
        else if (PyUnicode_Check(pKey))
        {
            // Attempt to convert string key to integer
            PyObject *long_key = PyNumber_Long(pKey);
            if (long_key)
            {
                qubit_index = PyLong_AsLong(long_key);
                Py_DECREF(long_key);
            }
            else
            {
                printf("Warning: Could not convert key to integer\n");
                continue;
            }
        }
        else
        {
            printf("Warning: Unexpected key type\n");
            continue;
        }

        Py_ssize_t list_len = PyList_Size(pValue);
        printf("Processing qubit %ld: %zd baseband samples\n", qubit_index, list_len);

        // Allocate memory for this qubit's waveform array
        qubit = (char ***)realloc(qubit, (qubit_count + 1) * sizeof(char **));
        arry_counts = (int *)realloc(arry_counts, ((qubit_count + 1) * sizeof(int)));
        wave_arry = (char **)malloc(list_len * sizeof(char *));

        int arry_count = 0;

        for (Py_ssize_t i = 0; i < list_len; i++)
        {
            PyObject *item = PyList_GetItem(pValue, i);
            double envelope_real, envelope_imag;

            // Parse baseband envelope as complex number
            if (parse_python_complex(item, &envelope_real, &envelope_imag))
            {
                // Generate carrier signal (cosine + sine) at time t
                double t = i * dt;
                double carrier_real = cos(2 * M_PI * carrier_freq * t);
                double carrier_imag = sin(2 * M_PI * carrier_freq * t);

                // IQ modulation: multiply envelope by carrier, take real part
                double real_waveform = complex_multiply_real_part(envelope_real, envelope_imag,
                                                                  carrier_real, carrier_imag);

                // Convert modulated sample to string
                double_to_string(real_waveform, &(wave_arry[i]));
                arry_count++;

                // Print first 5 samples for debugging
                if (i < 5)
                {
                    printf("  Sample %zd: envelope=(%.6f, %.6fj) -> modulated=%.6f\n",
                           i, envelope_real, envelope_imag, real_waveform);
                }
            }
            else
            {
                printf("Warning: Failed to parse complex value at index %zd\n", i);
                wave_arry[i] = strdup("0.000000"); // Default value on parse failure
                arry_count++;
            }
        }
        arry_counts[qubit_count] = arry_count;
        qubit[qubit_count] = wave_arry;
        qubit_count++;

        printf("Qubit %ld: successfully modulated %d samples\n", qubit_index, arry_count);
    }

    // Write all qubit waveform data to a single output file
    if (qubit_count > 0)
    {
        printf("\n=== Writing all qubit waveform data to file ===\n");
        char base_filename[256];
        const char *last_slash = strrchr(file, '/');
        const char *filename_only = last_slash ? last_slash + 1 : file;

        // Strip file extension for base filename
        strncpy(base_filename, filename_only, sizeof(base_filename) - 1);
        base_filename[sizeof(base_filename) - 1] = '\0';

        char *dot = strrchr(base_filename, '.');
        if (dot)
            *dot = '\0';

        // Use default name if base filename is empty
        if (strlen(base_filename) == 0)
        {
            strcpy(base_filename, "waveform");
        }

        // Write waveform data to file
        FILE *fp;
        char filename[50];
        sprintf(filename, "../data/all_qubits.txt");

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
            printf("Successfully wrote waveform data to %s\n", filename);
        }
    }

cleanup:
    // Release Python objects
    Py_DECREF(p_arrys);
    Py_DECREF(pModule);
    // Note: Py_Finalize() is commented out intentionally to allow multiple calls
    // in the same process without re-initializing the interpreter.
    printf("qubit_count is: %d\n", qubit_count);
    *q_count = qubit_count;
    *a_counts = arry_counts;

    return qubit;
}

/**
 * @brief Print IQ-modulated qubit waveform summary (for debugging)
 *
 * For each qubit, prints the first 10 modulated sample values; if there are more,
 * displays the remaining count.
 *
 * @param[in] qubit       Three-dimensional waveform array qubit[qubit_index][sample_index]
 * @param[in] qubit_count Total number of qubits
 * @param[in] arry_counts Array of waveform sample counts per qubit
 */
void qubit_print_modulated_waveforms(char ***qubit, int qubit_count, int *arry_counts)
{
    printf("\n=== Modulated Real Waveforms (After IQ Modulation) ===\n");
    for (int i = 0; i < qubit_count; i++)
    {
        printf("Qubit %d: %d modulated samples\n", i, arry_counts[i]);

        // Print first 10 samples only
        int print_count = (arry_counts[i] < 10) ? arry_counts[i] : 10;

        printf("  First %d modulated samples:\n", print_count);
        for (int j = 0; j < print_count; j++)
        {
            printf("    [%d]: %s\n", j, qubit[i][j]);
        }

        if (arry_counts[i] > 10)
        {
            printf("  ... and %d more samples\n", arry_counts[i] - 10);
        }

        printf("\n");
    }
}

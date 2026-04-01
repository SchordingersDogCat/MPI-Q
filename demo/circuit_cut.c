// Example: Execute a large-scale quantum circuit, with final results aggregated to each classical server

// Each host runs one process: mpirun a.out -config

// The mapping from qubits to boards, boards to hosts, and configuration information for waveform transmission data are all stored in a json configuration file

#include <mpi.h>
#include <stdio.h>

#define C_Num 2
#define C_Q 0  // Classical to Quantum
#define Q_C 1  // Quantum to Classical

int main(int argc, char** argv) {
	QMPI_Init(&argc, &argv);

	int rank, size;
	QMPI_Comm_rank(QMPI_COMM_WORLD, &rank);
	QMPI_Comm_size(QMPI_COMM_WORLD, &size);

	int send_data = [["H0", "X0", "M0"], ["CX1", "M1"], ["CZ2", "M2"], ["T3", "M3"]];    // A certain circuit to be executed by the application
	/*At this stage, it is necessary to determine which waveform data each board should send*/
	int recv_data[size];                        // Array for receiving data from all processes


	if (rank == 0) {
		// cards, hosts = process(send_data,"config.json");   // Process the data to be sent and determine the board information where these circuits are located
		// TODO: Multi-threading should be created here
		for (card in cards) {                     // Need to send data to specific node processes
			//preprocess(send_data);            // e.g., convert circuits to waveforms, etc.
			/*locate(card): Locate the specific host process through the board number*/
			QMPI_Send(C_Q, &send_data, data_len, MPI_INT,   // The target process can be located by identifying the board through the sent data
				locate(card), MPI_INT, MPI_COMM_WORLD);	// Classical -> Quantum process
		}
		for (card in cards) {                     // Need to receive data back from each board
			QMPI_Recv(Q_C, &recv_data, 1, MPI_Int, locate(card), QMPI_COMM_WORLD);  // Send the board's results to the main process in a non-blocking waiting manner
		}
		QMPI_Barrier(); // After waiting for all data to be returned
		// Analyze the result
		// Start the next iteration
	}
	else {
		QMPI_Recv(C_Q, &recv_data, 1, MPI_INT,       // Determine where the data comes from
			0, MPI_COMM_WORLD);	    // Classical to Quantum
		// QMPI_Barrier         // Perform data synchronization
		// Call the board driver to send data to the waveform generation interface
		// Call the board driver to send data to the read channel
		// Call the board driver to read data (recv_data) from the read channel
		// QMPI_Send(Q_C, &recv_data, 1, MPI_Int, 0, MPI_COMM_WORLD);  // Aggregate results to process 0
	}

	// Print the received data
	printf("Process %d received data: ", rank);
	for (int i = 0; i < size; i++) {
		printf("%d ", recv_data[i]);
	}
	printf("\n");

	QMPI_Finalize();
	return 0;

}
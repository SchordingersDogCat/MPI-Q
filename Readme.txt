# What is MPIQ?
With the development of superconducting quantum computer architecture towards large-scale and distributed directions, cross-node communication between classical control systems and quantum devices faces challenges such as high latency, complex processes, and low performance. This project proposes a distributed communication protocol called MPIQ (Classical-Quantum Message Passing Interface) for the "classical + quantum" architecture. It aims to reduce communication latency by minimizing data transmission overhead through lightweight protocol design, improve communication efficiency by supporting multi-node parallel communication and traffic optimization, enhance compatibility by adapting to the heterogeneous communication requirements between classical computing nodes and quantum measurement-control boards, and ensure the reliable transmission of quantum operation instructions through error checking and retransmission mechanisms to guarantee reliability.project

# Features and Advantages of MPIQ:
1) Compatible with classical parallel programming models, making it easy to get started and improving programming efficiency;
2) Provides standardized programming interfaces to enhance program portability and scalability;
3) Fully leverages the parallel computing capabilities of both classical and quantum systems to improve application runtime performance.

# Installation Guide
1) git clone https://gitee.com/vincentwang11/MPIQ.git
2) sudo apt install mpich
3) pip install -r requirements.txt

#Compilation Guide
1) cd your path to MPIQ
2) make

#File Structure
0) The program in the MPIQ is the library functions.
1) The program in the demo is used to simulate quantum computing.
2) The conf directory contains the config.json configuration file.
3) The data directory contains some utilized data.
4) The server component functions as a daemon process.
5) The programs in the test directory are test cases.

#Usage Method:
0) cd server
1) mpirun -np <number_of_IPs> ./server_user
2) cd test
3) To run test_all_gather using mpirun while ensuring other test cases execute normally, you can use the following command:
 mpirun -np <number_of_processes> ./test_all_gather

#Attention
0) In the Makefile, FINDLIB needs to be changed to the directory containing the Python interpreter, LDPY needs to be changed to the directory containing the Python libraries,  and LDPYLIBS should be changed to the corresponding Python interpreter.
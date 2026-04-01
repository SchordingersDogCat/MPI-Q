/*守护进程端，mpiq_monitor 使用MPIQ_Recv接收qasm文件，保存在指定路径下；
用命令行的方式调用qcsub_simu.py，读取qasm文件并完成子线路的模拟器执行等；
而后使用MPIQ_Send将执行的结果返回用户端 mpiq_user.c
用法：
    编译 gcc -o mpiq_monitor mpiq_monitor.c mpiq.c
    执行（启动多个接收端） ./mpiq_monitor 8888 ./subresult_0
                        ./mpiq_monitor 8889 ./subresult_1
                        ./mpiq_monitor 8890 ./subresult_2
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/time.h>
#include "mpiq.h"
#include <mpi.h>

#define MAX_CMD_LEN 4096
#define MAX_PATH_LEN 512
#define MAX_FILES 100

int execute_qcsub_simu(int rank, const char *qasm_dir, const char *output_dir);
int collect_result_files(const char *result_dir, char *target_dir);

int main(int argc, char *argv[])
{
    // 初始化 MPI 环境
    MPI_Init(&argc, &argv);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 3)
    {
        if (rank == 0)
        {
            printf("Usage: %s <port> <output_dir>\n", argv[0]);
            printf("Example: %s 8888 ./subresult\n", argv[0]);
        }
        MPI_Finalize();
        return 1;
    }

    int base_port = atoi(argv[1]);
    int port = base_port + rank; // 每个进程使用不同的端口

    // 用户指定的输出目录（如 ./result_monitor/subresult）
    // 每个进程会在此基础上添加 _rank 后缀（如 ./result_monitor/subresult_0）
    char output_dir[MAX_PATH_LEN];
    snprintf(output_dir, sizeof(output_dir), "%s_%d", argv[2], rank); // 每个进程使用不同的输出目录

    // 确保基础目录存在（使用 mkdir -p 创建多级目录）
    char base_dir[MAX_PATH_LEN];
    snprintf(base_dir, sizeof(base_dir), "%s", argv[2]);

    // 创建多级目录
    char cmd[MAX_CMD_LEN];
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", base_dir);
    system(cmd);

    // 确定处理的子线路索引
    int target_subcircuit;
    if (rank == 0)
        target_subcircuit = 0;
    else if (rank == 1)
        target_subcircuit = 1;
    else if (rank == 2)
        target_subcircuit = 2;
    else
        target_subcircuit = 1; // 进程3及以上都处理subcircuit_1

    // 创建子目录用于保存 QASM 文件
    char qasm_dir[MAX_PATH_LEN];
    snprintf(qasm_dir, sizeof(qasm_dir), "%s/subcircuit_%d", output_dir, target_subcircuit);

    // 创建目录结构（使用 mkdir -p 创建多级目录）
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", output_dir);
    system(cmd);
    snprintf(cmd, sizeof(cmd), "mkdir -p %s", qasm_dir);
    system(cmd);

    printf("========================================\n");
    printf("MPIQ Monitor Started\n");
    printf("Port: %d\n", port);
    printf("Output Directory: %s\n", output_dir);
    printf("QASM Directory: %s\n", qasm_dir);
    printf("Process Rank: %d\n", rank);
    printf("Total Processes: %d\n", size);
    printf("Processing Subcircuit: %d\n", target_subcircuit);
    printf("========================================\n\n");

    printf("========================================\n");
    printf("Step 1: Receiving QASM files from user...\n");
    printf("========================================\n");

    int recv_result = MPIQ_Recv(port, qasm_dir, target_subcircuit);

    if (recv_result == 0)
    {
        printf("QASM files received successfully!\n\n");

        printf("========================================\n");
        printf("Step 2: Executing qcsub_simu.py...\n");
        printf("========================================\n");

        // 记录子线路执行开始时间
        struct timeval start_time, end_time;
        // 同步所有进程到子线路执行前一刻
        MPI_Barrier(MPI_COMM_WORLD);
        gettimeofday(&start_time, NULL);

        int simu_result = execute_qcsub_simu(rank, qasm_dir, output_dir);

        // 等待所有进程完成子线路执行
        MPI_Barrier(MPI_COMM_WORLD);
        // 记录子线路执行完成时间
        gettimeofday(&end_time, NULL);
        double elapsed_time = (end_time.tv_sec - start_time.tv_sec) + (end_time.tv_usec - start_time.tv_usec) / 1000000.0;

        // 读取本进程的 process_list 执行时间
        double process_time = 0.0;
        char time_file[MAX_PATH_LEN];
        snprintf(time_file, sizeof(time_file), "%s/execution_time.txt", output_dir);
        FILE *fp = fopen(time_file, "r");
        if (fp != NULL)
        {
            fscanf(fp, "%lf", &process_time);
            fclose(fp);
        }

        // 收集所有进程的 process_list 执行时间，找到最大值
        double max_process_time;
        MPI_Reduce(&process_time, &max_process_time, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

        // 只在主进程中输出计时结果
        if (rank == 0)
        {
            printf("========================================\n");
            printf("子线路执行时间统计\n");
            printf("========================================\n");
            printf("通过操作系统提交量子程序进行噪声模拟的最大时间: %.6f 秒\n", max_process_time);
            printf("========================================\n\n");
        }

        if (simu_result == 0)
        {
            printf("qcsub_simu.py executed successfully!\n\n");

            printf("========================================\n");
            printf("Step 3: Collecting result files...\n");
            printf("========================================\n");

            char result_dir[MAX_PATH_LEN];
            snprintf(result_dir, sizeof(result_dir), "%s/result_cir", output_dir);

            char send_dir[MAX_PATH_LEN];
            snprintf(send_dir, sizeof(send_dir), "%s/send_results", output_dir);

            if (collect_result_files(result_dir, send_dir) < 0)
            {
                printf("Failed to collect result files!\n");
                return 1;
            }

            printf("Result files collected successfully!\n\n");

            printf("========================================\n");
            printf("Step 4: Sending results back to user...\n");
            printf("========================================\n");

            int send_result = MPIQ_Send_Results("127.0.0.1", port, send_dir);

            if (send_result == 0)
            {
                printf("Results sent back successfully!\n");
                printf("\n========================================\n");
                printf("MPIQ Monitor completed successfully!\n");
                printf("========================================\n");
            }
            else
            {
                printf("Failed to send results back!\n");
                return 1;
            }
        }
        else
        {
            printf("qcsub_simu.py executed unsuccessfully!\n");
            return 1;
        }
    }
    else
    {
        printf("Failed to receive QASM files!\n");
        return 1;
    }

    // 结束 MPI 环境
    MPI_Finalize();
    return 0;
}

int execute_qcsub_simu(int rank, const char *qasm_dir, const char *output_dir)
{
    char cmd[MAX_CMD_LEN];
    int cmd_len;

    printf("QASM Directory: %s\n", qasm_dir);
    printf("Output Directory: %s\n", output_dir);
    printf("Process Rank: %d\n", rank);

    // 根据进程 rank 调用不同的 qcsub_simu 脚本
    cmd_len = snprintf(cmd, sizeof(cmd),
                       "python qcsub_simu_%d.py -q %s/*.qasm -o %s -cut -b Simulator",
                       rank, qasm_dir, output_dir);

    if (cmd_len >= MAX_CMD_LEN)
    {
        fprintf(stderr, "Error: Command too long\n");
        return -1;
    }

    printf("Executing: %s\n", cmd);

    int ret = system(cmd);

    if (ret == -1)
    {
        fprintf(stderr, "Error: Failed to execute command\n");
        return -1;
    }

    return WEXITSTATUS(ret);
}

int collect_result_files(const char *result_dir, char *target_dir)
{
    DIR *dir = opendir(result_dir);
    if (dir == NULL)
    {
        perror("Failed to open result directory");
        return -1;
    }

    mkdir(target_dir, 0755);

    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL)
    {
        if (entry->d_type == DT_DIR && strncmp(entry->d_name, "circuit_", 8) == 0)
        {
            char circuit_path[MAX_PATH_LEN];
            snprintf(circuit_path, sizeof(circuit_path), "%s/%s", result_dir, entry->d_name);

            DIR *subdir = opendir(circuit_path);
            if (subdir != NULL)
            {
                struct dirent *subentry;
                while ((subentry = readdir(subdir)) != NULL)
                {
                    if (subentry->d_type == DT_DIR && strncmp(subentry->d_name, "subcircuit_", 11) == 0)
                    {
                        char subcircuit_path[MAX_PATH_LEN];
                        snprintf(subcircuit_path, sizeof(subcircuit_path), "%s/%s", circuit_path, subentry->d_name);

                        DIR *resultdir = opendir(subcircuit_path);
                        if (resultdir != NULL)
                        {
                            struct dirent *resultentry;
                            while ((resultentry = readdir(resultdir)) != NULL)
                            {
                                if (resultentry->d_type == DT_REG)
                                {
                                    char src_path[MAX_PATH_LEN];
                                    char dst_path[MAX_PATH_LEN];

                                    snprintf(src_path, sizeof(src_path), "%s/%s", subcircuit_path, resultentry->d_name);
                                    snprintf(dst_path, sizeof(dst_path), "%s/%s/%s/%s",
                                             target_dir, entry->d_name, subentry->d_name, resultentry->d_name);

                                    char *dirpath = strdup(dst_path);
                                    char *last_slash = strrchr(dirpath, '/');
                                    if (last_slash != NULL)
                                    {
                                        *last_slash = '\0';
                                        mkdir(dirpath, 0755);
                                    }
                                    free(dirpath);

                                    FILE *src = fopen(src_path, "rb");
                                    FILE *dst = fopen(dst_path, "wb");

                                    if (src && dst)
                                    {
                                        char buffer[BUFFER_SIZE];
                                        size_t bytes;
                                        while ((bytes = fread(buffer, 1, BUFFER_SIZE, src)) > 0)
                                        {
                                            fwrite(buffer, 1, bytes, dst);
                                        }
                                        printf("  Collected: %s\n", resultentry->d_name);
                                    }

                                    if (src)
                                        fclose(src);
                                    if (dst)
                                        fclose(dst);
                                }
                            }
                            closedir(resultdir);
                        }
                    }
                }
                closedir(subdir);
            }
        }
    }

    closedir(dir);
    return 0;
}

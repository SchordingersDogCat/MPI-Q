/*用户端，mpiq_user 用命令行的方式调用qcsub_cut.py，切割ghz_100.qasm并编译子线路，子线路保存在./result/compiled_qasms/subcircuit;
然后使用MPIQ_Send将不同子线路的qasm文件发送给不同守护进程端；
而后使用MPIQ_Recv接收守护进程端的模拟器执行结果；
最后调用qcsub_post.py完成结果重构。
用法：
    编译 gcc -o mpiq_user mpiq_user.c mpiq.c
    执行 ./mpiq_user
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

#define MAX_CMD_LEN 4096
#define MAX_PATH_LEN 512

int execute_qcsub_cut(const char *input_file, const char *output_path, const char *cut_method, int subcirc_qubits);
int execute_qcsub_post(const char *result_dir, const char *output_dir);

int main(int argc, char *argv[])
{
    const char *python_excutable = "python";
    char input_file[256] = "qasms/ghz/ghz_40.qasm";
    char *cut_method = "manual";
    int subcirc_qubits = 20;
    char output_path[256] = "./result";
    int qasm_port_base = 8888;
    int num_processes = 3; // 默认3个进程（对应subcircuit_0,1,2）

    // 解析命令行参数
    if (argc > 1)
    {
        num_processes = atoi(argv[1]);
        if (num_processes < 3)
        {
            num_processes = 3; // 至少3个进程
        }
        printf("Number of processes: %d\n", num_processes);
    }
    else
    {
        printf("Usage: %s <num_processes>\n", argv[0]);
        printf("Example: %s 4\n", argv[0]);
        return 1;
    }

    printf("========================================\n");
    printf("Step 1: Executing qcsub_cut.py...\n");
    printf("========================================\n");

    int ret = execute_qcsub_cut(input_file, output_path, cut_method, subcirc_qubits);

    if (ret == 0)
    {
        printf("qcsub_cut.py executed successfully!\n\n");

        printf("========================================\n");
        printf("Step 2: Sending QASM files to monitors...\n");
        printf("========================================\n");

        char base_path[MAX_PATH_LEN];
        snprintf(base_path, sizeof(base_path), "%s/compiled_qasms/circuit_0", output_path);

        DIR *dir = opendir(base_path);
        if (dir == NULL)
        {
            printf("Error: Cannot open directory %s\n", base_path);
            return 1;
        }

        struct dirent *entry;
        int success_count = 0;
        int total_subcircuits = 0;

        while ((entry = readdir(dir)) != NULL)
        {
            if (entry->d_type == DT_DIR && strncmp(entry->d_name, "subcircuit_", 11) == 0)
            {
                char subcircuit_path[MAX_PATH_LEN];
                snprintf(subcircuit_path, sizeof(subcircuit_path), "%s/%s", base_path, entry->d_name);

                // 从目录名中提取子电路索引
                int subcircuit_idx;
                if (sscanf(entry->d_name, "subcircuit_%d", &subcircuit_idx) == 1)
                {
                    // 基本端口映射：subcircuit_0→8888, subcircuit_1→8889, subcircuit_2→8890
                    int target_port = qasm_port_base + subcircuit_idx;
                    printf("\nSending files from %s to port %d\n", subcircuit_path, target_port);

                    int result = MPIQ_Send("127.0.0.1", target_port, subcircuit_path, subcircuit_idx);

                    if (result == 0)
                    {
                        printf("Successfully sent files to port %d\n", target_port);
                        success_count++;
                    }
                    else
                    {
                        printf("Failed to send files to port %d\n", target_port);
                    }
                    total_subcircuits++;

                    // 对于 subcircuit_1，额外发送给进程3及以上
                    if (subcircuit_idx == 1 && num_processes > 3)
                    {
                        // 向进程3及以上发送subcircuit_1
                        for (int extra_port = qasm_port_base + 3; extra_port < qasm_port_base + num_processes; extra_port++)
                        {
                            printf("\nSending subcircuit_1 files to extra port %d\n", extra_port);
                            int extra_result = MPIQ_Send("127.0.0.1", extra_port, subcircuit_path, subcircuit_idx);
                            if (extra_result == 0)
                            {
                                printf("Successfully sent subcircuit_1 files to extra port %d\n", extra_port);
                                success_count++;
                                total_subcircuits++;
                            }
                            else
                            {
                                printf("Failed to send subcircuit_1 files to extra port %d\n", extra_port);
                            }
                        }
                    }
                }
                else
                {
                    printf("Warning: Invalid subcircuit directory name: %s\n", entry->d_name);
                }
            }
        }

        closedir(dir);
        printf("\n========================================\n");
        printf("Step 2 completed!\n");
        printf("Successful sends: %d/%d\n", success_count, total_subcircuits);
        printf("========================================\n");

        if (success_count == total_subcircuits && success_count > 0)
        {
            // 记录发送完成时间
            struct timeval send_end_time;
            gettimeofday(&send_end_time, NULL);
            double send_elapsed = send_end_time.tv_sec + send_end_time.tv_usec / 1000000.0;
            printf("\n[计时] 发送子线路完成，累计时间: %.6f 秒\n", send_elapsed);

            printf("\n========================================\n");
            printf("Step 3: Receiving results from monitors...\n");
            printf("========================================\n");

            int recv_success_count = 0;
            int recv_total_subcircuits = 0;

            // 重新打开目录，获取所有子电路目录
            DIR *recv_dir = opendir(base_path);
            if (recv_dir == NULL)
            {
                printf("Error: Cannot open directory %s\n", base_path);
                return 1;
            }

            struct dirent *recv_entry;
            while ((recv_entry = readdir(recv_dir)) != NULL)
            {
                if (recv_entry->d_type == DT_DIR && strncmp(recv_entry->d_name, "subcircuit_", 11) == 0)
                {
                    int subcircuit_idx;
                    if (sscanf(recv_entry->d_name, "subcircuit_%d", &subcircuit_idx) == 1)
                    {
                        int target_port = qasm_port_base + subcircuit_idx;
                        printf("\nReceiving results from port %d\n", target_port);

                        int result = MPIQ_Recv(target_port, output_path, subcircuit_idx);

                        if (result == 0)
                        {
                            printf("Successfully received results from port %d\n", target_port);
                            recv_success_count++;
                        }
                        else
                        {
                            printf("Failed to receive results from port %d\n", target_port);
                        }
                        recv_total_subcircuits++;
                    }
                }
            }
            closedir(recv_dir);

            // 接收进程3及以上的结果（处理subcircuit_1）
            if (num_processes > 3)
            {
                printf("\n========================================\n");
                printf("Receiving results from extra processes...\n");
                printf("========================================\n");

                for (int extra_port = qasm_port_base + 3; extra_port < qasm_port_base + num_processes; extra_port++)
                {
                    printf("\nReceiving results from extra port %d\n", extra_port);

                    int result = MPIQ_Recv(extra_port, output_path, 1); // 1 表示 subcircuit_1

                    if (result == 0)
                    {
                        printf("Successfully received results from extra port %d\n", extra_port);
                        recv_success_count++;
                    }
                    else
                    {
                        printf("Failed to receive results from extra port %d\n", extra_port);
                    }
                    recv_total_subcircuits++;
                }
            }

            // 记录接收完成时间
            struct timeval recv_end_time;
            gettimeofday(&recv_end_time, NULL);
            double total_elapsed = recv_end_time.tv_sec + recv_end_time.tv_usec / 1000000.0;
            double comm_elapsed = total_elapsed - send_elapsed;

            printf("\n========================================\n");
            printf("Step 3 completed!\n");
            printf("Successful receives: %d/%d\n", recv_success_count, recv_total_subcircuits);
            printf("========================================\n");

            printf("\n========== 通信时间统计 ==========\n");
            printf("发送子线路完成时间: %.6f 秒\n", send_elapsed);
            printf("接收结果完成时间: %.6f 秒\n", total_elapsed);
            printf("发送子线路到接收结果的通信时间: %.6f 秒\n", comm_elapsed);
            printf("==================================\n");

            if (recv_success_count == recv_total_subcircuits)
            {
                printf("\n========================================\n");
                printf("Step 4: Executing qcsub_post.py...\n");
                printf("========================================\n");

                int post_result = execute_qcsub_post(output_path, output_path);

                if (post_result == 0)
                {
                    printf("qcsub_post.py executed successfully!\n");
                    printf("\n========================================\n");
                    printf("All steps completed successfully!\n");
                    printf("========================================\n");
                }
                else
                {
                    printf("qcsub_post.py executed unsuccessfully!\n");
                    return 1;
                }
            }
            else
            {
                printf("\nError: Not all results received successfully!\n");
                return 1;
            }
        }
        else
        {
            printf("\nError: Not all subcircuits sent successfully!\n");
            return 1;
        }
    }
    else
    {
        printf("qcsub_cut.py executed unsuccessfully!\n");
        return 1;
    }

    return 0;
}

int execute_qcsub_cut(const char *input_file, const char *output_path, const char *cut_method, int subcirc_qubits)
{
    char cmd[MAX_CMD_LEN];
    snprintf(cmd, sizeof(cmd),
             "python qcsub_cut.py -i %s -o %s -cut -cut_method %s -subcirc_qubits %d",
             input_file,
             output_path,
             cut_method,
             subcirc_qubits);

    printf("Command: %s\n", cmd);

    int ret = system(cmd);

    if (ret == -1)
    {
        fprintf(stderr, "Error: Failed to execute command\n");
        return -1;
    }

    return WEXITSTATUS(ret);
}

int execute_qcsub_post(const char *result_dir, const char *output_dir)
{
    char cmd[MAX_CMD_LEN];
    int cmd_len;

    printf("Result Directory: %s/result_cir\n", result_dir);
    printf("Output Directory: %s\n", output_dir);

    cmd_len = snprintf(cmd, sizeof(cmd),
                       "python qcsub_post.py -r %s/result_cir -o %s -cut",
                       result_dir, output_dir);

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

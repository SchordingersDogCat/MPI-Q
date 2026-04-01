#include <iostream>
#include <vector>
#include <tuple>
#include <string>
#include <map>
#include <set>
#include <cmath>
#include <fstream>
#include <regex>
#include <chrono>
#include <algorithm>

using namespace std;
using namespace std::chrono;

typedef tuple<string, string> Tag;
typedef tuple<Tag, map<string, double>> InfoItem;
typedef tuple<Tag, map<string, double>> ResultItem;

// 函数：将文件内容读取为字符串
string readFileToString(const string& filePath) {
    ifstream file(filePath);
    if (!file.is_open()) {
        cerr << "无法打开文件: " << filePath << endl;
        exit(1);
    }
    string content((istreambuf_iterator<char>(file)), istreambuf_iterator<char>());
    file.close();
    return content;
}

vector<InfoItem> parseInfoItems(const string& content) {
    vector<InfoItem> items;
    regex itemRegex(R"(\(\(\s*['\"](.+?)['\"],\s*['\"](.+?)['\"]\s*\),\s*\{([^\}]*)\}\))");
    smatch match;
    
    string contentCopy = content;
    while (regex_search(contentCopy, match, itemRegex)) {
        string initTag = match[1].str();
        string measTag = match[2].str();
        string countsStr = match[3].str();
        
        Tag tag = make_tuple(initTag, measTag);
        map<string, double> counts;
        
        regex countRegex(R"(['\"](.+?)['\"]\s*:\s*([\d\.eE+-]+))");
        smatch countMatch;
        
        string countsCopy = countsStr;
        while (regex_search(countsCopy, countMatch, countRegex)) {
            string key = countMatch[1].str();
            string valueStr = countMatch[2].str();
            double value = stod(valueStr);
            counts[key] = value;
            countsCopy = countMatch.suffix().str();
        }
        
        items.emplace_back(tag, counts);
        contentCopy = match.suffix().str();
    }
    
    return items;
}

// 函数：从文件内容解析多个 InfoItem 数据集
vector<vector<InfoItem>> parseMultipleDatasets(const string& content) {
    vector<vector<InfoItem>> datasets;
    
    regex datasetRegex(R"(\[(.*?)\])");
    smatch datasetMatch;
    
    string contentCopy = content;
    while (regex_search(contentCopy, datasetMatch, datasetRegex)) {
        string datasetStr = datasetMatch[1].str();
        vector<InfoItem> dataset = parseInfoItems(datasetStr);
        datasets.emplace_back(dataset);
        contentCopy = datasetMatch.suffix().str();
    }
    
    return datasets;
}

vector<vector<InfoItem>> readMultipleDatasetsFromFile(const string& filePath) {
    string content = readFileToString(filePath);
    return parseMultipleDatasets(content);
}

// 重构两个相邻子线路的概率分布，支持所有标签组合，并基于极值优化
vector<ResultItem> reconstruct_pair(const vector<ResultItem>& up_info, const vector<InfoItem>& down_info, double scale_factor = 1.0) {
    vector<string> init_tags = {"0", "1", "+", "i", "none"};
    vector<string> meas_tags = {"I", "Z", "X", "Y", "none"};
    vector<ResultItem> p_rec_list;

    for (const string& init_tag : init_tags) {
        for (const string& meas_tag : meas_tags) {
            Tag new_tag = make_tuple(init_tag, meas_tag);
            map<string, double> p_rec;

            vector<ResultItem> rec_up_info;
            for (const auto& item : up_info) {
                const Tag& tag = get<0>(item);
                if (get<0>(tag) == init_tag) {
                    rec_up_info.emplace_back(item);
                }
            }

            vector<InfoItem> rec_down_info;
            for (const auto& item : down_info) {
                const Tag& tag = get<0>(item);
                if (get<1>(tag) == meas_tag) {
                    rec_down_info.emplace_back(item);
                }
            }

            if (rec_up_info.empty() || rec_down_info.empty()) {
                continue;
            }

            set<string> substring2_set;
            vector<pair<Tag, map<string, double>>> adjusted_p2_info;
            for (const auto& item : rec_down_info) {
                const Tag& tag = get<0>(item);
                const map<string, double>& counts = get<1>(item);
                if (!counts.empty()) {
                    vector<pair<string, double>> sorted_items(counts.begin(), counts.end());
                    sort(sorted_items.begin(), sorted_items.end(), [](const pair<string, double>& a, const pair<string, double>& b) {
                        return a.second > b.second;
                    });

                    map<string, double> top_counts;
                    int length;
                    if (get<0>(tag) == "0" || get<0>(tag) == "1") {
                        length = static_cast<int>(ceil(sorted_items.size() * scale_factor * 2));
                        for (int i = 0; i < length && i < static_cast<int>(sorted_items.size()); ++i) {
                            top_counts[sorted_items[i].first] = sorted_items[i].second;
                            substring2_set.insert(sorted_items[i].first);
                        }
                    } else if (get<0>(tag) == "+" || get<0>(tag) == "i") {
                        sort(sorted_items.begin(), sorted_items.end(), [](const pair<string, double>& a, const pair<string, double>& b) {
                            return a.second < b.second;
                        });
                        length = static_cast<int>(ceil(sorted_items.size() * scale_factor));
                        for (int i = 0; i < length && i < static_cast<int>(sorted_items.size()); ++i) {
                            top_counts[sorted_items[i].first] = sorted_items[i].second;
                            substring2_set.insert(sorted_items[i].first);
                        }
                    }
                    adjusted_p2_info.emplace_back(tag, top_counts);
                } else {
                    substring2_set.insert("0");
                    adjusted_p2_info.emplace_back(tag, map<string, double>{{"0", 0.0}});
                }
            }

            set<string> substring1_set;
            vector<pair<Tag, map<string, double>>> adjusted_p1_info;
            for (const auto& item : rec_up_info) {
                const Tag& tag = get<0>(item);
                const map<string, double>& counts = get<1>(item);
                if (!counts.empty()) {
                    vector<pair<string, double>> sorted_items(counts.begin(), counts.end());
                    sort(sorted_items.begin(), sorted_items.end(), [](const pair<string, double>& a, const pair<string, double>& b) {
                        return a.second > b.second;
                    });

                    map<string, double> top_counts;
                    int length;
                    if (get<1>(tag) == "I" || get<1>(tag) == "Z") {
                        length = static_cast<int>(ceil(sorted_items.size() * scale_factor));
                        for (int i = 0; i < length && i < static_cast<int>(sorted_items.size()); ++i) {
                            string key = sorted_items[i].first;
                            if (key.size() > 1) {
                                substring1_set.insert(key.substr(1));
                            } else if (key.size() == 1) {
                                substring1_set.insert("");
                            }
                            top_counts[key] = sorted_items[i].second;
                        }
                    } else if (get<1>(tag) == "X" || get<1>(tag) == "Y") {
                        sort(sorted_items.begin(), sorted_items.end(), [](const pair<string, double>& a, const pair<string, double>& b) {
                            return a.second < b.second;
                        });
                        length = static_cast<int>(ceil(sorted_items.size() * scale_factor));
                        for (int i = 0; i < length && i < static_cast<int>(sorted_items.size()); ++i) {
                            string key = sorted_items[i].first;
                            if (key.size() > 1) {
                                substring1_set.insert(key.substr(1));
                            } else if (key.size() == 1) {
                                substring1_set.insert("");
                            }
                            top_counts[key] = sorted_items[i].second;
                        }
                    }
                    adjusted_p1_info.emplace_back(tag, top_counts);
                } else {
                    substring1_set.insert("0");
                    adjusted_p1_info.emplace_back(tag, map<string, double>{{"0", 0.0}});
                }
            }

            for (const string& substring2 : substring2_set) {
                for (const string& substring1 : substring1_set) {
                    string string_full = substring2 + substring1;
                    string substring11 = "0" + substring1;
                    string substring12 = "1" + substring1;

                    vector<double> p1(4, 0.0);
                    vector<double> p2(4, 0.0);

                    for (const auto& item : adjusted_p1_info) {
                        const Tag& tag = item.first;
                        const map<string, double>& counts = item.second;
                        string meas = get<1>(tag);
                        if (meas == "I" || meas == "Z") {
                            p1[0] = counts.count(substring11) ? counts.at(substring11) * 2 : 0.0;
                            p1[1] = counts.count(substring12) ? counts.at(substring12) * 2 : 0.0;
                        } else if (meas == "X") {
                            p1[2] = (counts.count(substring11) ? counts.at(substring11) : 0.0) - 
                                    (counts.count(substring12) ? counts.at(substring12) : 0.0);
                        } else if (meas == "Y") {
                            p1[3] = (counts.count(substring11) ? counts.at(substring11) : 0.0) - 
                                    (counts.count(substring12) ? counts.at(substring12) : 0.0);
                        }
                    }

                    double p21 = 0.0;
                    double p22 = 0.0;
                    for (const auto& item : adjusted_p2_info) {
                        const Tag& tag = item.first;
                        const map<string, double>& counts = item.second;
                        string init = get<0>(tag);
                        if (init == "0") {
                            p21 = counts.count(substring2) ? counts.at(substring2) : 0.0;
                            p2[0] = p21;
                        } else if (init == "1") {
                            p22 = counts.count(substring2) ? counts.at(substring2) : 0.0;
                            p2[1] = p22;
                        }
                    }

                    for (const auto& item : adjusted_p2_info) {
                        const Tag& tag = item.first;
                        const map<string, double>& counts = item.second;
                        string init = get<0>(tag);
                        if (init == "+") {
                            p2[2] = 2 * (counts.count(substring2) ? counts.at(substring2) : 0.0) - p21 - p22;
                        } else if (init == "i") {
                            p2[3] = 2 * (counts.count(substring2) ? counts.at(substring2) : 0.0) - p21 - p22;
                        }
                    }

                    double p = 0.0;
                    for (int i = 0; i < 4; ++i) {
                        p += p1[i] * p2[i];
                    }
                    p /= 2.0;

                    if (p > 0) {
                        p_rec[string_full] = p;
                    }
                }
            }

            double total = 0.0;
            for (const auto& pair : p_rec) {
                total += pair.second;
            }
            if (total > 0.0) {
                for (auto& pair : p_rec) {
                    pair.second /= total;
                }
            }

            p_rec_list.emplace_back(new_tag, p_rec);
        }
    }

    return p_rec_list;
}

void printAndSaveFinalResults(const vector<ResultItem>& results, const string& outputFilePath, int topN = 100) {
    ofstream outFile(outputFilePath);
    if (!outFile.is_open()) {
        cerr << "无法打开输出文件: " << outputFilePath << endl;
        return;
    }

    // outFile << "===== 最终重构结果 (按value降序排列, 前" << topN << "个) =====" << endl;
    
    for (const auto& item : results) {
        const Tag& tag = get<0>(item);
        const map<string, double>& counts = get<1>(item);
        
        // 将map转换为vector以便排序
        vector<pair<string, double>> sortedCounts(counts.begin(), counts.end());
        // 按value降序排序
        sort(sortedCounts.begin(), sortedCounts.end(), [](const pair<string, double>& a, const pair<string, double>& b) {
            return a.second > b.second;
        });
        
        // outFile << "Tag: (" << get<0>(tag) << ", " << get<1>(tag) << "):" << endl;
        
        // 写入前topN个结果
        int written = 0;
        for (const auto& count : sortedCounts) {
            if (written >= topN) break;
            outFile << count.first << ": " << count.second << endl;
            written++;
        }
        // if (sortedCounts.size() > topN) {
        //     outFile << "  ... (共" << sortedCounts.size() << "项，仅显示前" << topN << "个)" << endl;
        // }
        // outFile << "------------------------" << endl;
    }
    
    outFile.close();
    cout << "前" << topN << "个结果已保存至: " << outputFilePath << endl;
}

int main(int argc, char** argv) {
    // 记录程序开始时间

    auto start_time = high_resolution_clock::now();
    
    // 检查是否提供了输入和输出路径
    if (argc != 5) {
        std::cerr << "用法: " << argv[0] << " --input <输入文件路径> --output <输出文件路径>" << std::endl;
        return 1;
    }

    std::string input_file_path, output_file_path;
    for (int i = 1; i < argc; i += 2) {
        if (strcmp(argv[i], "--input") == 0 && i + 1 < argc) {
            input_file_path = argv[i + 1];
        } else if (strcmp(argv[i], "--output") == 0 && i + 1 < argc) {
            output_file_path = argv[i + 1];
        }
    }

    if (input_file_path.empty() || output_file_path.empty()) {
        std::cerr << "输入路径或输出路径未指定" << std::endl;
        return 1;
    }

    vector<vector<InfoItem>> datasets = readMultipleDatasetsFromFile(input_file_path);

    vector<ResultItem> current_result;
    int call_count = 0;

    if (datasets.size() >= 2) {
        vector<InfoItem> first_info = datasets[0];
        vector<InfoItem> second_info = datasets[1];
        
        auto start = high_resolution_clock::now();
        current_result = reconstruct_pair(first_info, second_info);
        auto end = high_resolution_clock::now();
        // auto duration = duration_cast<seconds>(end - start);
        auto duration_ms = duration_cast<milliseconds>(end - start);
        double duration_sec = static_cast<double>(duration_ms.count()) / 1000.0;        
        call_count++;
        // cout << "第 " << call_count << " 次调用 reconstruct_pair 耗时: " << duration_sec << " 秒" << endl;
        printf("第 %d 次调用 reconstruct_pair 耗时: %.3f 秒\n", call_count, duration_sec);
    }

    for (size_t i = 2; i < datasets.size(); ++i) {
        vector<InfoItem> next_info = datasets[i];
        
        auto start = high_resolution_clock::now();
        current_result = reconstruct_pair(current_result, next_info);
        auto end = high_resolution_clock::now();
        // auto duration = duration_cast<seconds>(end - start);
        auto duration_ms = duration_cast<milliseconds>(end - start);
        double duration_sec = static_cast<double>(duration_ms.count()) / 1000.0;           
        call_count++;
        // cout << "第 " << call_count << " 次调用 reconstruct_pair 耗时: " << duration_sec << " 秒" << endl;
        printf("第 %d 次调用 reconstruct_pair 耗时: %.3f 秒\n", call_count, duration_sec);
    }

    // 按value排序并保存前100个结果
    const string outputPath = output_file_path;
    printAndSaveFinalResults(current_result, outputPath, 100);

    // 记录程序结束时间并计算总运行时间
    auto end_time = high_resolution_clock::now();

    // auto total_duration = duration_cast<seconds>(end_time - start_time);
    auto duration_ms = duration_cast<milliseconds>(end_time - start_time);
    double duration_sec = static_cast<double>(duration_ms.count()) / 1000.0;   
    // cout << "程序总运行时间: " << duration_sec << " 秒" << endl;
    printf("重构程序总运行时间: %.3f 秒\n", duration_sec);
    return 0;
}
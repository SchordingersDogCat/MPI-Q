#include <iostream>
#include <vector>
#include <tuple>
#include <string>
#include <map>
#include <set>
#include <cmath>
#include <fstream>
#include <regex>
#include <algorithm>
#include <sstream>
#include <mpi.h>
#include <numeric>
#include <climits>
#include <list>
#include <omp.h> // Add OpenMP header file

using namespace std;

// Define aliases for custom data types
typedef tuple<string, string> Tag;
typedef pair<Tag, map<string, double>> InfoItem;
typedef pair<Tag, map<string, double>> ResultItem;

// --- Helper function: Print dataset information ---
void print_dataset_info(const vector<ResultItem>& dataset, const string& context, int rank) {
    cout << "    [Print Rank " << rank << "]: " << context << " | Dataset size: " << dataset.size() << " Tag-map pairs." << endl;
    if (dataset.empty()) {
        cout << "      -> (Dataset is empty)" << endl;
        return;
    }
    // Print detailed information for debugging in the final stage
    for (size_t i = 0; i < min((size_t)4, dataset.size()); ++i) { // Only print first few items to keep logs concise
        const auto& item = dataset[i];
        cout << "      -> Item " << i << ": Tag(" << get<0>(item.first) << ", " << get<1>(item.first) << "), Map size: " << item.second.size() << endl;
    }
    if (dataset.size() > 4) {
        cout << "      -> ... (and " << dataset.size() - 4 << " more items)" << endl;
    }
}

// --- Serialization/Deserialization helper functions ---
string serialize_map(const map<string, double>& m) {
    stringstream ss;
    ss << m.size() << "\n";
    for (const auto& pair : m) {
        ss << pair.first << "\n" << pair.second << "\n";
    }
    return ss.str();
}

map<string, double> deserialize_map(stringstream& ss) {
    map<string, double> m;
    size_t map_size;
    ss >> map_size;
    ss.ignore();
    for (size_t i = 0; i < map_size; ++i) {
        string key;
        double value;
        getline(ss, key);
        ss >> value;
        ss.ignore();
        m[key] = value;
    }
    return m;
}

string serialize_results(const vector<ResultItem>& results) {
    stringstream ss;
    ss << results.size() << "\n";
    for (const auto& item : results) {
        ss << get<0>(item.first) << "\n";
        ss << get<1>(item.first) << "\n";
        ss << serialize_map(item.second);
    }
    return ss.str();
}

vector<ResultItem> deserialize_results_from_stream(stringstream& ss) {
    vector<ResultItem> results;
    size_t results_size;
    ss >> results_size;
    ss.ignore();
    for (size_t i = 0; i < results_size; ++i) {
        string init_tag, meas_tag;
        getline(ss, init_tag);
        getline(ss, meas_tag);
        Tag tag = make_tuple(init_tag, meas_tag);
        map<string, double> counts = deserialize_map(ss);
        results.emplace_back(tag, counts);
    }
    return results;
}

vector<ResultItem> deserialize_results(const string& data) {
    stringstream ss(data);
    return deserialize_results_from_stream(ss);
}

string serialize_work_chunk(const vector<vector<ResultItem>>& chunk) {
    stringstream ss;
    ss << chunk.size() << "\n";
    for (const auto& result_vec : chunk) {
        ss << serialize_results(result_vec);
    }
    return ss.str();
}

vector<vector<ResultItem>> deserialize_work_chunk(const string& data) {
    vector<vector<ResultItem>> chunk;
    if (data.empty()) return chunk;
    stringstream ss(data);
    size_t chunk_size;
    ss >> chunk_size;
    ss.ignore();
    for (size_t i = 0; i < chunk_size; ++i) {
        chunk.push_back(deserialize_results_from_stream(ss));
    }
    return chunk;
}

// --- File reading and parsing functions (unchanged) ---
string readFileToString(const string& filePath) {
    ifstream file(filePath);
    if (!file.is_open()) {
        cerr << "Failed to open file: " << filePath << endl;
        exit(1);
    }
    string content((istreambuf_iterator<char>(file)), istreambuf_iterator<char>());
    file.close();
    return content;
}

vector<InfoItem> parseInfoItems(const string& content) {
    vector<InfoItem> items;
    // Regex compatible with pairs and tuples
    regex itemRegex(R"(\(\s*\(\s*['\"]([^'\"]*)['\"]\s*,\s*['\"]([^'\"]*)['\"]\s*\)\s*,\s*\{([^\}]*)\}\))");
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
            counts[countMatch[1].str()] = stod(countMatch[2].str());
            countsCopy = countMatch.suffix().str();
        }
        items.emplace_back(tag, counts);
        contentCopy = match.suffix().str();
    }
    return items;
}

vector<vector<InfoItem>> parseMultipleDatasets(const string& content) {
    vector<vector<InfoItem>> datasets;
    regex datasetRegex(R"(\[((?:\s*\(\s*\(\s*['\"]([^'\"]*)['\"]\s*,\s*['\"]([^'\"]*)['\"]\s*\)\s*,\s*\{[^\}]*\}\s*\)\s*,?)*)\])");
    smatch datasetMatch;
    string contentCopy = content;

    while (regex_search(contentCopy, datasetMatch, datasetRegex)) {
        if (datasetMatch.length(1) > 0) {
            vector<InfoItem> dataset = parseInfoItems(datasetMatch[1].str());
            if (!dataset.empty()) {
                datasets.push_back(dataset);
            }
        }
        contentCopy = datasetMatch.suffix().str();
    }
    return datasets;
}

vector<vector<InfoItem>> readMultipleDatasetsFromFile(const string& filePath) {
    string content = readFileToString(filePath);
    return parseMultipleDatasets(content);
}

// --- Parallel task processing function ---
void parallel_reconstruct_task(
    const vector<ResultItem>& adjusted_p1_info,
    const vector<ResultItem>& adjusted_p2_info,
    const set<string>& substring1_set,
    const set<string>& substring2_set,
    map<string, double>& p_rec_final,
    int rank,
    int size
) {
    vector<pair<string, string>> work_items;
    if (rank == 0) {
        for (const string& s2 : substring2_set) {
            for (const string& s1 : substring1_set) {
                work_items.emplace_back(s2, s1);
            }
        }
        cout << "[Main process Rank 0]: Total number of work items: " << work_items.size() << ", preparing to distribute tasks to each process." << endl;
    }

    long long total_work = work_items.size();
    MPI_Bcast(&total_work, 1, MPI_LONG_LONG, 0, MPI_COMM_WORLD);

    if (total_work == 0) {
        MPI_Barrier(MPI_COMM_WORLD);
        return;
    }

    long long items_per_proc = total_work / size;
    long long remainder = total_work % size;

    string serialized_p1;
    int p1_size = 0;
    if (rank == 0) {
        serialized_p1 = serialize_results(adjusted_p1_info);
        p1_size = serialized_p1.size();
    }
    MPI_Bcast(&p1_size, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (p1_size > 0) {
        if (rank != 0) serialized_p1.resize(p1_size);
        MPI_Bcast(&serialized_p1[0], p1_size, MPI_CHAR, 0, MPI_COMM_WORLD);
    }

    string serialized_p2;
    int p2_size = 0;
    if (rank == 0) {
        serialized_p2 = serialize_results(adjusted_p2_info);
        p2_size = serialized_p2.size();
    }
    MPI_Bcast(&p2_size, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (p2_size > 0) {
        if (rank != 0) serialized_p2.resize(p2_size);
        MPI_Bcast(&serialized_p2[0], p2_size, MPI_CHAR, 0, MPI_COMM_WORLD);
    }

    vector<ResultItem> local_p1_info = deserialize_results(serialized_p1);
    vector<ResultItem> local_p2_info = deserialize_results(serialized_p2);

    vector<pair<string, string>> local_work_items;
    if (rank == 0) {
        long long current_pos = 0;
        for (int proc = 0; proc < size; ++proc) {
            long long num_to_assign = items_per_proc + (proc < remainder ? 1 : 0);
            vector<pair<string, string>> proc_work_items;
            if (current_pos < total_work) {
                long long end_pos = min(current_pos + num_to_assign, total_work);
                proc_work_items.assign(work_items.begin() + current_pos, work_items.begin() + end_pos);
                current_pos = end_pos;
            }

            stringstream ss;
            ss << proc_work_items.size() << "\n";
            for (const auto& item : proc_work_items) {
                ss << item.first << "\n" << item.second << "\n";
            }
            string serialized_proc_work = ss.str();
            int work_size = serialized_proc_work.size();

            if (proc == 0) {
                local_work_items = proc_work_items;
            }
            else {
                MPI_Send(&work_size, 1, MPI_INT, proc, 0, MPI_COMM_WORLD);
                if (work_size > 0) {
                    MPI_Send(serialized_proc_work.c_str(), work_size, MPI_CHAR, proc, 0, MPI_COMM_WORLD);
                }
            }
        }
    }
    else {
        int work_size;
        MPI_Recv(&work_size, 1, MPI_INT, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        if (work_size > 0) {
            string serialized_proc_work(work_size, '\0');
            MPI_Recv(&serialized_proc_work[0], work_size, MPI_CHAR, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            stringstream ss(serialized_proc_work);
            size_t num_items;
            ss >> num_items;
            ss.ignore();
            for (size_t i = 0; i < num_items; ++i) {
                string s1, s2;
                getline(ss, s1); getline(ss, s2);
                local_work_items.emplace_back(s1, s2);
            }
        }
    }

    stringstream log_ss;
    log_ss << "  [Data reception confirmation Rank " << rank << "]: Received " << local_work_items.size() << " work items." << endl;
    if (!local_work_items.empty() && local_work_items.size() < 5) {
        for (const auto& pair : local_work_items) {
            log_ss << "    -> s2: '" << pair.first << "', s1: '" << pair.second << "'" << endl;
        }
    }
    cout << log_ss.str();
    MPI_Barrier(MPI_COMM_WORLD);

    if (rank == 0) cout << "[All processes]: Work item distribution completed, starting local computation..." << endl;

    map<string, double> local_p_rec;
    for (size_t i = 0; i < local_work_items.size(); ++i) {
        const string& substring2 = local_work_items[i].first;
        const string& substring1 = local_work_items[i].second;
        string string_full = substring2 + substring1;
        string substring11 = "0" + substring1;
        string substring12 = "1" + substring1;
        vector<double> p1(4, 0.0), p2(4, 0.0);
        for (const auto& p1_item : local_p1_info) {
            const map<string, double>& counts = p1_item.second;
            string meas = get<1>(p1_item.first);
            if (meas == "I" || meas == "Z" || meas == "none") {
                p1[0] = counts.count(substring11) ? counts.at(substring11) * 2 : 0.0;
                p1[1] = counts.count(substring12) ? counts.at(substring12) * 2 : 0.0;
            }
            else if (meas == "X") {
                p1[2] = (counts.count(substring11) ? counts.at(substring11) : 0.0) - (counts.count(substring12) ? counts.at(substring12) : 0.0);
            }
            else if (meas == "Y") {
                p1[3] = (counts.count(substring11) ? counts.at(substring11) : 0.0) - (counts.count(substring12) ? counts.at(substring12) : 0.0);
            }
        }
        double p21 = 0.0, p22 = 0.0;
        for (const auto& p2_item : local_p2_info) {
            const map<string, double>& counts = p2_item.second;
            string init = get<0>(p2_item.first);
            if (init == "0" || init == "none") {
                p21 = counts.count(substring2) ? counts.at(substring2) : 0.0;
                p2[0] = p21;
            }
            else if (init == "1") {
                p22 = counts.count(substring2) ? counts.at(substring2) : 0.0;
                p2[1] = p22;
            }
        }
        for (const auto& p2_item : local_p2_info) {
            const map<string, double>& counts = p2_item.second;
            string init = get<0>(p2_item.first);
            if (init == "+") {
                p2[2] = 2 * (counts.count(substring2) ? counts.at(substring2) : 0.0) - p21 - p22;
            }
            else if (init == "i") {
                p2[3] = 2 * (counts.count(substring2) ? counts.at(substring2) : 0.0) - p21 - p22;
            }
        }
        double p = 0.0;
        for (int j = 0; j < 4; ++j) p += p1[j] * p2[j];
        p /= 2.0;
        if (p > 1e-9) {
            local_p_rec[string_full] = p;
        }
    }

    if (rank == 0) {
        p_rec_final = local_p_rec;
        for (int i = 1; i < size; ++i) {
            int incoming_size;
            MPI_Recv(&incoming_size, 1, MPI_INT, i, 2, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            if (incoming_size > 0) {
                string serialized_data(incoming_size, '\0');
                MPI_Recv(&serialized_data[0], incoming_size, MPI_CHAR, i, 2, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                stringstream ss(serialized_data);
                map<string, double> received_map = deserialize_map(ss);
                p_rec_final.insert(received_map.begin(), received_map.end());
            }
        }
    }
    else {
        string serialized_map = serialize_map(local_p_rec);
        int map_str_size = serialized_map.length();
        MPI_Send(&map_str_size, 1, MPI_INT, 0, 2, MPI_COMM_WORLD);
        if (map_str_size > 0) {
            MPI_Send(serialized_map.c_str(), map_str_size, MPI_CHAR, 0, 2, MPI_COMM_WORLD);
        }
    }

    if (rank == 0) {
        cout << "[Main process Rank 0]: Received local computation results from all processes, starting aggregation..." << endl;
        double total = 0.0;
        for (const auto& pair : p_rec_final) total += pair.second;
        if (total > 0.0) {
            for (auto& pair : p_rec_final) pair.second /= total;
        }

        vector<pair<string, double>> final_sorted_p_rec(p_rec_final.begin(), p_rec_final.end());
        size_t final_top_n = min((size_t)100, final_sorted_p_rec.size());
        if (final_top_n > 0) {
            auto final_middle_it = final_sorted_p_rec.begin() + final_top_n;
            partial_sort(final_sorted_p_rec.begin(), final_middle_it, final_sorted_p_rec.end(),
                [](const pair<string, double>& a, const pair<string, double>& b) {
                    return a.second > b.second;
                });
        }
        map<string, double> temp_map;
        for (size_t i = 0; i < final_top_n; ++i) {
            temp_map[final_sorted_p_rec[i].first] = final_sorted_p_rec[i].second;
        }
        p_rec_final = temp_map;
        cout << "[Main process Rank 0]: Final result processing completed, containing " << p_rec_final.size() << " items." << endl;
    }
    MPI_Barrier(MPI_COMM_WORLD);
}

// --- Core reconstruction function ---
vector<ResultItem> reconstruct_pair(const vector<ResultItem>& up_info, const vector<ResultItem>& down_info, double scale_factor = 1.0, bool parallelize = false) {
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    vector<string> init_tags = { "0", "1", "+", "i", "none" };
    vector<string> meas_tags = { "I", "Z", "X", "Y", "none" };
    vector<ResultItem> p_rec_list;

    for (size_t init_idx_loop = 0; init_idx_loop < init_tags.size(); ++init_idx_loop) {
        for (size_t meas_idx_loop = 0; meas_idx_loop < meas_tags.size(); ++meas_idx_loop) {
            const string& init_tag = init_tags[init_idx_loop];
            const string& meas_tag = meas_tags[meas_idx_loop];
            Tag new_tag = make_tuple(init_tag, meas_tag);
            map<string, double> p_rec;

            vector<ResultItem> rec_up_info;
            for (const auto& item : up_info) {
                if (get<0>(get<0>(item)) == init_tag) {
                    rec_up_info.push_back(item);
                }
            }

            vector<InfoItem> rec_down_info;
            for (const auto& item : down_info) {
                if (get<1>(get<0>(item)) == meas_tag) {
                    rec_down_info.push_back(item);
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

                    int length;
                    if (get<0>(tag) == "0" || get<0>(tag) == "1") {
                        length = static_cast<int>(ceil(sorted_items.size() * scale_factor * 2));
                        auto middle_it = sorted_items.begin() + min((size_t)length, sorted_items.size());
                        partial_sort(sorted_items.begin(), middle_it, sorted_items.end(),
                            [](const pair<string, double>& a, const pair<string, double>& b) {
                                return a.second > b.second;
                            });
                    }
                    else if (get<0>(tag) == "+" || get<0>(tag) == "i") {
                        length = static_cast<int>(ceil(sorted_items.size() * scale_factor));
                        auto middle_it = sorted_items.begin() + min((size_t)length, sorted_items.size());
                        partial_sort(sorted_items.begin(), middle_it, sorted_items.end(),
                            [](const pair<string, double>& a, const pair<string, double>& b) {
                                return a.second < b.second;
                            });
                    }

                    map<string, double> top_counts;
                    for (int i = 0; i < length && i < static_cast<int>(sorted_items.size()); ++i) {
                        top_counts[sorted_items[i].first] = sorted_items[i].second;
                        substring2_set.insert(sorted_items[i].first);
                    }
                    adjusted_p2_info.emplace_back(tag, top_counts);
                }
                else {
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

                    int length;
                    if (get<1>(tag) == "I" || get<1>(tag) == "Z") {
                        length = static_cast<int>(ceil(sorted_items.size() * scale_factor));
                        auto middle_it = sorted_items.begin() + min((size_t)length, sorted_items.size());
                        partial_sort(sorted_items.begin(), middle_it, sorted_items.end(),
                            [](const pair<string, double>& a, const pair<string, double>& b) {
                                return a.second > b.second;
                            });
                    }
                    else if (get<1>(tag) == "X" || get<1>(tag) == "Y") {
                        length = static_cast<int>(ceil(sorted_items.size() * scale_factor));
                        auto middle_it = sorted_items.begin() + min((size_t)length, sorted_items.size());
                        partial_sort(sorted_items.begin(), middle_it, sorted_items.end(),
                            [](const pair<string, double>& a, const pair<string, double>& b) {
                                return a.second < b.second;
                            });
                    }

                    map<string, double> top_counts;
                    for (int i = 0; i < length && i < static_cast<int>(sorted_items.size()); ++i) {
                        string key = sorted_items[i].first;
                        if (key.size() > 1) {
                            substring1_set.insert(key.substr(1));
                        }
                        else if (key.size() == 1) {
                            substring1_set.insert("");
                        }
                        top_counts[key] = sorted_items[i].second;
                    }
                    adjusted_p1_info.emplace_back(tag, top_counts);
                }
                else {
                    substring1_set.insert("0");
                    adjusted_p1_info.emplace_back(tag, map<string, double>{{"0", 0.0}});
                }
            }

            if (parallelize) {
                parallel_reconstruct_task(adjusted_p1_info, adjusted_p2_info, substring1_set, substring2_set, p_rec, rank, size);
            }
            else {
                vector<string> substring2_vec(substring2_set.begin(), substring2_set.end());
                vector<string> substring1_vec(substring1_set.begin(), substring1_set.end());

                // ************************** Code correction section **************************
                // Fixed compilation error from previous version.
                // The error was because default(none) requires explicit declaration of all variables' sharing properties.
                // Added cout, init_tag, and meas_tag to the shared clause here.
#pragma omp parallel default(none) shared(substring2_vec, substring1_vec, adjusted_p1_info, adjusted_p2_info, p_rec, rank, cout, init_tag, meas_tag)
                {
#pragma omp single
                    {
                        cout << "    [Thread count report Rank " << rank << "]: In the OpenMP parallel region of reconstruct_pair function (init_tag=" << init_tag << ", meas_tag=" << meas_tag << "), actually started " << omp_get_num_threads() << " threads." << endl;
                    }

#pragma omp for collapse(2) schedule(dynamic)
                    for (size_t s2_idx = 0; s2_idx < substring2_vec.size(); ++s2_idx) {
                        for (size_t s1_idx = 0; s1_idx < substring1_vec.size(); ++s1_idx) {
                            const string& substring2 = substring2_vec[s2_idx];
                            const string& substring1 = substring1_vec[s1_idx];
                            string string_full = substring2 + substring1;
                            string substring11 = "0" + substring1;
                            string substring12 = "1" + substring1;

                            vector<double> p1(4, 0.0);
                            vector<double> p2(4, 0.0);

                            for (const auto& item : adjusted_p1_info) {
                                const map<string, double>& counts = item.second;
                                string meas = get<1>(item.first);
                                if (meas == "I" || meas == "Z") {
                                    p1[0] = counts.count(substring11) ? counts.at(substring11) * 2 : 0.0;
                                    p1[1] = counts.count(substring12) ? counts.at(substring12) * 2 : 0.0;
                                }
                                else if (meas == "X") {
                                    p1[2] = (counts.count(substring11) ? counts.at(substring11) : 0.0) -
                                        (counts.count(substring12) ? counts.at(substring12) : 0.0);
                                }
                                else if (meas == "Y") {
                                    p1[3] = (counts.count(substring11) ? counts.at(substring11) : 0.0) -
                                        (counts.count(substring12) ? counts.at(substring12) : 0.0);
                                }
                            }

                            double p21 = 0.0;
                            double p22 = 0.0;
                            for (const auto& item : adjusted_p2_info) {
                                const map<string, double>& counts = item.second;
                                string init = get<0>(item.first);
                                if (init == "0") {
                                    p21 = counts.count(substring2) ? counts.at(substring2) : 0.0;
                                    p2[0] = p21;
                                }
                                else if (init == "1") {
                                    p22 = counts.count(substring2) ? counts.at(substring2) : 0.0;
                                    p2[1] = p22;
                                }
                            }

                            for (const auto& item : adjusted_p2_info) {
                                const map<string, double>& counts = item.second;
                                string init = get<0>(item.first);
                                if (init == "+") {
                                    p2[2] = 2 * (counts.count(substring2) ? counts.at(substring2) : 0.0) - p21 - p22;
                                }
                                else if (init == "i") {
                                    p2[3] = 2 * (counts.count(substring2) ? counts.at(substring2) : 0.0) - p21 - p22;
                                }
                            }

                            double p_val = 0.0;
                            for (int i = 0; i < 4; ++i) {
                                p_val += p1[i] * p2[i];
                            }
                            p_val /= 2.0;

                            if (p_val > 1e-9) {
#pragma omp critical
                                p_rec[string_full] = p_val;
                            }
                        }
                    }
                } // End #pragma omp parallel
                // ************************ End of correction ************************
            }

            if (!p_rec.empty()) {
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
    }

    return p_rec_list;
}

// --- Final result processing function ---
void printAndSaveFinalResults(const vector<ResultItem>& results, const string& outputFilePath) {
    ofstream outFile(outputFilePath);
    if (!outFile.is_open()) {
        cerr << "Failed to open output file: " << outputFilePath << endl;
        return;
    }
    const int top_n = 100;
    for (const auto& item : results) {
        const Tag& tag = item.first;
        const map<string, double>& counts = item.second;
        vector<pair<string, double>> sortedCounts(counts.begin(), counts.end());
        size_t output_top_n = min((size_t)top_n, sortedCounts.size());
        if (output_top_n > 0) {
            auto middle_it = sortedCounts.begin() + output_top_n;
            partial_sort(sortedCounts.begin(), middle_it, sortedCounts.end(),
                [](const pair<string, double>& a, const pair<string, double>& b) {
                    return a.second > b.second;
                });
        }

        outFile << "Tag: (" << get<0>(tag) << ", " << get<1>(tag) << ") - Top " << top_n << " Results:" << endl;
        for (size_t i = 0; i < output_top_n; ++i) {
            const auto& count = sortedCounts[i];
            outFile << count.first << ": " << count.second << endl;
        }
        outFile << "----------------------------------------" << endl;
    }
    outFile.close();
    cout << "Top " << top_n << " results for each tag have been saved to: " << outputFilePath << endl;
}

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (rank == 0) {
        cout << "[Main process Rank 0]: Setting OpenMP thread count..." << endl;
    }
    omp_set_num_threads(omp_get_max_threads());
    int actual_threads = omp_get_max_threads();
    cout << "[Process Rank " << rank << "]: OpenMP maximum thread count set to " << actual_threads << endl;

    double overall_start_time, overall_end_time;
    double computation_start_time, computation_end_time;
    overall_start_time = MPI_Wtime();

    list<vector<ResultItem>> work_queue;
    vector<ResultItem> final_result;

    if (rank == 0) {
        cout << "[Main process Rank 0]: MPI program started, total number of processes: " << size << endl;
        string filename = "/public/home/mscaosc/hefei/result_0.5/result_0.5/result_0.5.txt";
        vector<vector<InfoItem>> all_datasets_info = readMultipleDatasetsFromFile(filename);
        if (all_datasets_info.size() < 2) {
            cerr << "[Main process Rank 0] Error: At least 2 datasets are required for reconstruction." << endl;
            size_t signal = -1;
            MPI_Bcast(&signal, 1, MPI_UNSIGNED_LONG, 0, MPI_COMM_WORLD);
            MPI_Finalize();
            return 1;
        }
        cout << "[Main process Rank 0]: Loaded " << all_datasets_info.size() << " datasets from " << filename << ". Initializing work queue..." << endl;
        for (const auto& dataset : all_datasets_info) {
            work_queue.emplace_back(dataset.begin(), dataset.end());
        }
        cout << "[Main process Rank 0]: Work queue initialization completed, containing " << work_queue.size() << " task items." << endl;
    }

    computation_start_time = MPI_Wtime();

    int stage = 1;
    // --- Reduction loop ---
    while (true) {
        size_t queue_size;
        if (rank == 0) {
            queue_size = work_queue.size();
        }
        MPI_Bcast(&queue_size, 1, MPI_UNSIGNED_LONG, 0, MPI_COMM_WORLD);

        if (queue_size == (size_t)-1) {
            if (rank != 0) cerr << "[Worker process Rank " << rank << "]: Received exit signal, program terminating." << endl;
            MPI_Finalize();
            return 1;
        }

        if (queue_size <= 2) {
            break;
        }

        int num_active_procs = 0;
        if (rank == 0) {
            cout << "\n===== [Reduction stage " << stage << "]: " << queue_size << " task items to process. =====" << endl;
            size_t num_pairs = queue_size / 2;
            num_active_procs = min((int)num_pairs, size);
            cout << "    -> Can form " << num_pairs << " task pairs in this round, will activate " << num_active_procs << " processes for processing." << endl;
        }
        MPI_Bcast(&num_active_procs, 1, MPI_INT, 0, MPI_COMM_WORLD);

        if (rank == 0) {
            vector<vector<ResultItem>> tasks_for_this_round;
            tasks_for_this_round.reserve(num_active_procs * 2);
            for (int i = 0; i < num_active_procs * 2; ++i) {
                tasks_for_this_round.push_back(move(work_queue.front()));
                work_queue.pop_front();
            }

            list<vector<ResultItem>> unassigned_tasks = move(work_queue);
            cout << "    -> " << unassigned_tasks.size() << " task items will be retained at the end of the next round's queue." << endl;

            int num_workers = num_active_procs > 1 ? num_active_procs - 1 : 0;
            vector<string> sent_chunks(num_workers);
            for (int i = 0; i < num_workers; ++i) {
                int worker_rank = i + 1;
                vector<ResultItem>& phys_upstream = tasks_for_this_round[worker_rank * 2];
                vector<ResultItem>& phys_downstream = tasks_for_this_round[worker_rank * 2 + 1];

                cout << "\n--- [Sending task Rank 0 -> Rank " << worker_rank << "][Task pair " << worker_rank << "] ---" << endl;
                print_dataset_info(phys_upstream, "Upstream data to send (accumulated results)", 0);
                print_dataset_info(phys_downstream, "Downstream data to send (next dataset)", 0);

                vector<vector<ResultItem>> chunk_to_send = { phys_upstream, phys_downstream };
                sent_chunks[i] = serialize_work_chunk(chunk_to_send);
                int chunk_size = sent_chunks[i].size();

                MPI_Send(&chunk_size, 1, MPI_INT, worker_rank, 0, MPI_COMM_WORLD);
                MPI_Send(sent_chunks[i].c_str(), chunk_size, MPI_CHAR, worker_rank, 0, MPI_COMM_WORLD);
            }

            vector<ResultItem> local_result;
            if (num_active_procs > 0) {
                vector<ResultItem>& phys_upstream = tasks_for_this_round[0];
                vector<ResultItem>& phys_downstream = tasks_for_this_round[1];
                cout << "\n--- [Local merging Rank 0][Task pair 0] ---" << endl;
                print_dataset_info(phys_upstream, "Upstream data (accumulated results)", 0);
                print_dataset_info(phys_downstream, "Downstream data (next dataset)", 0);
                local_result = reconstruct_pair(phys_upstream, phys_downstream, 0.1, false);
                print_dataset_info(local_result, "New dataset generated by local merging", 0);
            }

            vector<vector<ResultItem>> collected_results;
            collected_results.reserve(num_active_procs);
            if (num_active_procs > 0) {
                collected_results.push_back(move(local_result));
            }

            if (num_workers > 0) {
                cout << "\n--- [Receiving results in order Rank 1-" << num_workers << "] ---" << endl;
            }
            for (int i = 0; i < num_workers; ++i) {
                int worker_rank = i + 1;
                int result_size;
                MPI_Recv(&result_size, 1, MPI_INT, worker_rank, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);

                string serialized_result(result_size, '\0');
                MPI_Recv(&serialized_result[0], result_size, MPI_CHAR, worker_rank, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);

                vector<ResultItem> received_result = deserialize_results(serialized_result);
                cout << "  [Main process Rank 0]: <- Received merged results from Rank " << worker_rank << "." << endl;
                print_dataset_info(received_result, "Received intermediate results", 0);
                collected_results.push_back(move(received_result));
            }

            list<vector<ResultItem>> next_round_queue;
            for (auto& res : collected_results) {
                next_round_queue.push_back(move(res));
            }
            next_round_queue.splice(next_round_queue.end(), unassigned_tasks);

            work_queue = move(next_round_queue);
            cout << "\n[Main process Rank 0]: Current round reduction completed, next round queue size: " << work_queue.size() << endl;

        }
        else {
            if (rank < num_active_procs) {
                int chunk_size;
                MPI_Recv(&chunk_size, 1, MPI_INT, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                string serialized_chunk(chunk_size, '\0');
                MPI_Recv(&serialized_chunk[0], chunk_size, MPI_CHAR, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);

                vector<vector<ResultItem>> my_work = deserialize_work_chunk(serialized_chunk);

                if (my_work.size() == 2) {
                    vector<ResultItem>& phys_upstream = my_work[0];
                    vector<ResultItem>& phys_downstream = my_work[1];
                    cout << "\n--- [Task processing Rank " << rank << "] ---" << endl;
                    print_dataset_info(phys_upstream, "Received upstream data (accumulated results)", rank);
                    print_dataset_info(phys_downstream, "Received downstream data (next dataset)", rank);

                    vector<ResultItem> local_result = reconstruct_pair(phys_upstream, phys_downstream, 0.1, false);
                    print_dataset_info(local_result, "New dataset generated by local merging", rank);

                    string serialized_result = serialize_results(local_result);
                    int result_size = serialized_result.size();

                    cout << "[Worker process Rank " << rank << "]: Merging completed, sending results to main process..." << endl;
                    MPI_Send(&result_size, 1, MPI_INT, 0, 1, MPI_COMM_WORLD);
                    MPI_Send(serialized_result.c_str(), result_size, MPI_CHAR, 0, 1, MPI_COMM_WORLD);
                }
                else {
                    cerr << "[Worker process Rank " << rank << "] Error: Received task chunk size is not 2, cannot process." << endl;
                }
            }
        }

        stage++;
        MPI_Barrier(MPI_COMM_WORLD);
    }

    bool perform_final_parallel_step = false;
    if (rank == 0) {
        if (work_queue.size() == 2) {
            perform_final_parallel_step = true;
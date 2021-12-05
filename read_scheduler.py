import numpy as np
import json
import matplotlib.pyplot as plt
import math

negative_infinity = float('-inf')                                                                    #
def max_list_of_lists(list):
    size_list = len(list)
    max_aux = negative_infinity
    for i in range(size_list):
        if list[i] != []:
            max_aux = max([max_aux, max(list[i])])
    return max_aux

# ------------------------------------------------------
#
#                       ANALYSIS
#
# ------------------------------------------------------
file_name = 'results_test_case_1.json'
f = open(file_name, "r")

x = json.load(f)

N_nodes = x[0]
comm_graph =  x[1]
rate_in =  x[2]
total_rate_in = x[3]
delay_network = x[4]
mana = x[5]
total_mana = x[6]
Qtotal = x[7]
nu = x[8]
max_messages = x[9]
time_of_beggining_of_new_round = x[10]
messages_received = x[11]
time_received = x[12]
node_of_issuance = x[13]

f.close()

length_of_rounds = [[] for i in range(N_nodes)]                                                     # |\
average_length_of_rounds_per_node = [0 for i in range(N_nodes)]                                     # |\ list initialization
total_average_length_of_rounds = 0                                                                  # |/
total_number_of_rounds = 0                                                                          # |/

for i in range(N_nodes):                                                                                                                        # |\
    number_of_rounds = len(time_of_beggining_of_new_round[i]) - 1                                                                               # |\
    if number_of_rounds > 0:                                                                                                                    # |\
        length_of_rounds[i] = [time_of_beggining_of_new_round[i][j+1]-time_of_beggining_of_new_round[i][j] for j in range(number_of_rounds)]    # |\ 
        average_length_of_rounds_per_node[i] = sum(length_of_rounds[i])/number_of_rounds                                                        # |\ statistics of length of rounds (total and per node)
        total_average_length_of_rounds = total_average_length_of_rounds + sum(length_of_rounds[i])                                              # |/ it should be common to ALL nodes (not depending on being content, BE etc)
        total_number_of_rounds = total_number_of_rounds + number_of_rounds                                                                      # |/
#print(average_length_of_rounds_per_node)                                                                                                        # |/
if total_number_of_rounds > 0:                                                                                                                  # |/
    round_length = total_average_length_of_rounds/total_number_of_rounds                                                                               # |/
else: 
    round_length = 0

node_to_be_studied = int(np.random.uniform(0, N_nodes))                                                             # |\
number_of_rounds = len(time_of_beggining_of_new_round[node_to_be_studied]) - 1                                      # |\
messages_received_per_round_per_node = [[0 for j in range(N_nodes)] for i in range(number_of_rounds)]               # |\
j = 0                                                                                                               # |\ statistics of the behaviour of a single (random) scheduler
for i in range(number_of_rounds):                                                                                   # |  the stats from each queue should depend on the regime of the issuer (BE, content etc)
    while time_received[node_to_be_studied][j] < time_of_beggining_of_new_round[node_to_be_studied][i]:             # |/
        aux = node_of_issuance[messages_received[node_to_be_studied][j]]                                            # |/
        messages_received_per_round_per_node[i][aux] = messages_received_per_round_per_node[i][aux] + 1             # |/
        j = j + 1                                                                                                   # |/
    
#print(messages_received_per_round_per_node)
#print(length_of_rounds[node_to_be_studied])
#print(node_to_be_studied)

all_nodes = False

if all_nodes == True:
    for i in range(N_nodes):
        maximum = max_list_of_lists(messages_received_per_round_per_node)
        #print(i, np.mean([messages_received_per_round_per_node[j][i] for j in range(number_of_rounds)]), np.var([messages_received_per_round_per_node[j][i] for j in range(number_of_rounds)]))
        a = [messages_received_per_round_per_node[j][i] for j in range(number_of_rounds)]
        hist, bin_edges = np.histogram(a, bins=np.arange(maximum), density=True)
        print(hist)
        edges_list = list(bin_edges)
        x_array = [(edges_list[i]+edges_list[i+1])/2 for i in range(len(edges_list)-1)]
        #plt.hist(a, bins=max(a), density=True)
        label = 'node'+str(i)
        plt.plot(x_array, hist, 'o', label=label)
        plt.legend()
    plt.show()
else:
    node = 1
    #print(i, np.mean([messages_received_per_round_per_node[j][node] for j in range(number_of_rounds)]), np.var([messages_received_per_round_per_node[j][node] for j in range(number_of_rounds)]))
    a = [messages_received_per_round_per_node[j][node] for j in range(number_of_rounds)]
    if len(a) != 0:
        hist, bin_edges = np.histogram(a, bins=np.arange(max(a)), density=True)
        print(hist)
        edges_list = list(bin_edges)
        x_array = [(edges_list[i]+edges_list[i+1])/2 for i in range(len(edges_list)-1)]
        #plt.hist(a, bins=max(a), density=True)
        label = 'node '+str(node)
        plt.plot(x_array, hist, 'o', label=label)
        plt.legend()
        lambd = rate_in[node]*round_length
        poisson = [math.exp(-lambd)]
        for i in range(len(x_array)-1):
            poisson.append(poisson[-1]*lambd/(i+1))
        print(poisson)
        plt.plot(x_array, poisson , 'x', label=label)    
plt.show()



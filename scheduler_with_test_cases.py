import numpy as np
import json
import random
from networkx import connected_watts_strogatz_graph
from networkx import neighbors
import sys

N_nodes = 20                                                                                        
rate_in = [0, 0, 0.5, 0.5, 1, 1, 1.5, 1.5, 2, 2, 0, 0, 2, 2, 4, 4, 6, 6, 8, 8]                                                                           
total_rate_in = sum(rate_in)                                                                       
mana = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]                                   
total_mana = sum(mana)                                                                              
#print(total_rate_in, total_mana)
nu = 50
Inactive_nodes = [0, 1, 10, 11] 
Strictly_content_nodes = [2, 3, 12, 13]
Content_nodes = [4, 5, 14, 15]
Circumstantially_content_nodes = [6, 7, 16, 17]
Best_effort_nodes = [8, 9, 18, 19]
Low_mana_nodes = [i for i in range(10)]
High_mana_nodes = [10+i for i in range(10)]

file_name = sys.argv[1]
f = open(file_name)
x = json.load(f)
f.close()

# G1 = high granularity
# G2 = mixed granularity
# G3 = low granularity
Test_case_granularity = x[0]

# D1 = constant delay
# D2 = random delay
Test_case_delay = x[1]

# T1 = complete graph
# T2 = random graph
# T3 = ring graph
Test_case_topology = x[2]

test_case_name = 'test_case_G' + str(Test_case_granularity) + '_D' + str(Test_case_delay) + '_T' + str(Test_case_topology)

if Test_case_topology == 1:
    comm_graph = [[1 for j in range(N_nodes)] for i in range(N_nodes)]                                  
elif Test_case_topology == 2:
    comm_graph = [[0 for j in range(N_nodes)] for i in range(N_nodes)]                                  
    aux = connected_watts_strogatz_graph(N_nodes, 4, 0.5, tries=100, seed=None)
    for i in range(N_nodes):
        for j in aux.neighbors(i):
            comm_graph[i][j] = 1                                  
else:
    comm_graph = [[0 for j in range(N_nodes)] for i in range(N_nodes)]  
    aux = [i for i in range(N_nodes)] 
    random.shuffle(aux)
    comm_graph[aux[0]][aux[-1]] = 1
    comm_graph[aux[0]][aux[1]] = 1
    comm_graph[aux[-1]][aux[-2]] = 1
    comm_graph[aux[-1]][aux[0]] = 1
    for i in range(1, N_nodes-1):
        comm_graph[aux[i]][aux[i-1]] = 1
        comm_graph[aux[i]][aux[i+1]] = 1

base_delay = 0.01
distance_graph = [[np.random.uniform(0, 2*base_delay) for j in range(N_nodes)] for i in range(N_nodes)]  
for i in range(N_nodes):
    for j in range(i):
        distance_graph[i][j] = distance_graph[j][i]

def random_delay(i, j):
    if Test_case_delay == 1:
        delay_network = base_delay                                                                           
    else:
        delay_network = np.random.gamma(distance_graph[i][j], scale=1.0, size=None)
    return delay_network

Qtotal_vector = [10, 25, 100]     
Qtotal = Qtotal_vector[Test_case_granularity-1]                                                                              

max_messages = 1_000_000

# NODES INITIALIZATION
buffers = [[[] for j in range(N_nodes)] for i in range(N_nodes)]                                    #
deficits = [[0 for j in range(N_nodes)] for i in range(N_nodes)]                                    #
last_queue_being_scheduled = [int(np.random.uniform(0, N_nodes)) for i in range(N_nodes)]           # to do = play with this initialization (it should not make any difference...)
initial_queue = last_queue_being_scheduled.copy()                                                   # auxiliary vector to help counting the rounds
next_scheduling_event = [np.random.uniform(0, 1/nu) for i in range(N_nodes)]                        # to do = play with this initialization
time_of_beggining_of_new_round = [[next_scheduling_event[i]] for i in range(N_nodes)]               # auxiliary vector, it should not make any difference
messages_received = [[] for i in range(N_nodes)]                                                    # historic of all messages received by each node
time_received = [[] for i in range(N_nodes)]                                                        # historic of the time when the messages above were received
messages_to_be_enqueued = [[] for i in range(N_nodes)]                                              # auxiliary vector with the messages that should be enqueued by each node
time_to_be_enqueued = [[] for i in range(N_nodes)]                                                  # auxiliary vector with the time that the messages above should be enqueued
unknown_messages = [[] for i in range(N_nodes)]                                                     # auxiliary vector to check if the messages received are known to the node. the 1st version of the code used the vector messages_received, but since this list grows linearly with time, the program got slow. unknown_messages is roughly constant with time, so the speed improved a lot

# MESSAGES INITALIZATION
message_number = 0                                                                                  # this 1st entry should be ignored from the stats    
time_of_issuance = [0]                                                                              # this 1st entry should be ignored from the stats
node_of_issuance = [-1]                                                                             # this 1st entry should be ignored from the stats

# SIMULATION PROPERTIES
positive_infinity = float('inf')                                                                    #
filtered_next_scheduling_event = [positive_infinity for i in range(N_nodes)]                        # auxiliary vector. It is used to store the "actual" next scheduling event in each node (in particular, if the buffers are empty, the next value is infinity)


# ------------------------------------------------------
#
#                       FUNCTIONS
#
# ------------------------------------------------------

# This function makes 'node' to schedule and gossip the next message in its buffer, at 'time_now'
# This function should not be called if the buffer is empty (it will be a infinite loop in this case), but the main part of the program takes care of that. 
def schedule_and_gossip(node, time_now, last_queue_being_scheduled, deficits, buffers, messages_received, time_received, messages_to_be_enqueued, time_to_be_enqueued, next_scheduling_event):
    schedule_queue_number = last_queue_being_scheduled[node]                                                                                # it starts in the last queue visited by the node's scheduler
    while buffers[node][schedule_queue_number] == [] or deficits[node][schedule_queue_number] < 1:                                          # |\ 
        if schedule_queue_number == N_nodes - 1 :                                                                                           # |\
            schedule_queue_number = 0                                                                                                       # | it will jump to a subsequent queue while nothing can be scheduled in the present queue
        else:                                                                                                                               # |/
            schedule_queue_number = schedule_queue_number + 1                                                                               # |/
        deficits[node][schedule_queue_number] = deficits[node][schedule_queue_number] + mana[schedule_queue_number]/total_mana*Qtotal       # whenever a queue is visited, the deficit for this queue is updated
        if schedule_queue_number == initial_queue[node]:                                                                                    # |\ this part only checks if a new round has begun and stores the time it started (auxiliary, does not change the scheduler behaviour)
            time_of_beggining_of_new_round[node].append(time_now)                                                                           # |/
        last_queue_being_scheduled[node] = schedule_queue_number                                                                            # updates the last queue visited
    message_to_be_scheduled = buffers[node][schedule_queue_number][0]                                                                       # checks the first message in the queue selected to scheduling
    gossip_to = comm_graph[node]                                                                                                            # this list stores to which nodes the message scheduled should be gossiped
    for i in range(N_nodes):                                                                                                                # |\ gossip to the list above
        if gossip_to[i] == 1:                                                                                                               # |/
            if message_to_be_scheduled in unknown_messages[i]:                                                                              # checks is this message was already received in the past by the node
                delay = random_delay(node, i)
                unknown_messages[i].remove(message_to_be_scheduled)                                                                         # removes the message from that list, since now it is known
                messages_received[i].append(message_to_be_scheduled)                                                                        # adds the message to the history of received messages
                index_aux = 1 + next((j for j in range(len(time_to_be_enqueued[i])-1, -1, -1) if time_to_be_enqueued[i][j] <= time_now + delay ), -1)
                messages_to_be_enqueued[i].insert(index_aux, message_to_be_scheduled)
                #messages_to_be_enqueued[i].append(message_to_be_scheduled)                                                                 # adds the message to the list of messages to be enqueued
                time_received[i].append(time_now + delay)                                                                                   # adds the time that the message was received (and enqueued) to the history
                #time_to_be_enqueued[i].append(time_now + delay)                                                                            # adds the time that the message is supposed to be enqueued
                time_to_be_enqueued[i].insert(index_aux, time_now + delay)
                if time_to_be_enqueued[i] != sorted(time_to_be_enqueued[i]):
                    raise NameError('Wrong test case number') 
    deficits[node][schedule_queue_number] = deficits[node][schedule_queue_number] - 1                                                       # deficit update (subtract 1 since the message was scheduled)
    buffers[node][schedule_queue_number].pop(0)                                                                                             # remove the scheduled message from the head of the queue
    next_scheduling_event[node] = time_now + 1/nu                                                                                           # update the next scheduling event

# This function returns 'True' if the buffer of 'node' is empty and 'False' otherwise
def is_buffer_empty(node, buffers):
    aux = True
    for j in range(N_nodes):                                                                                                    
        if buffers[node][j] != []:                                                                                                 
            aux = False
    return aux

# This function enqueues every message that should be enqueued before 'time'
def enqueue(time, time_to_be_enqueued, messages_to_be_enqueued, buffers, next_scheduling_event, node_of_issuance):
    for i in range(N_nodes):                                                                                                                # 
        if time_to_be_enqueued[i] != []:                                                                                                    # if there is something to be enqueued
            while time_to_be_enqueued[i][0] <= time:                                                                                        # and it should be enqueued before 'time'
                message_aux = messages_to_be_enqueued[i][0]                                                                                 # checks the number of the first message to be enqueued
                node_aux = node_of_issuance[message_aux]                                                                                    # checks who issued the message (and thus to which queue it belongs)                                                                                            #
                if is_buffer_empty(i, buffers) == True and next_scheduling_event[i] < time_to_be_enqueued[i][0]:                            # |\ nothing is scheduled if there is nothing to be scheduled, so the next_scheduling_event should be postponed when the buffer is empty   
                    next_scheduling_event[i] = time_to_be_enqueued[i][0]                                                                    # |/
                buffers[i][node_aux].append(message_aux)                                                                                    # |\ 
                time_to_be_enqueued[i].pop(0)                                                                                               # | enqueued = added to the buffer and removed from the "to be enqueued" list
                messages_to_be_enqueued[i].pop(0)                                                                                           # |/
                if time_to_be_enqueued[i] == []:                                                                                            # ugly step to make it work
                    break                                                                                                                   #


# This function returns the minimum value of a nested list
def min_list_of_lists(list):
    size_list = len(list)
    min_aux = positive_infinity
    for i in range(size_list):
        if list[i] != []:
            min_aux = min([min_aux, min(list[i])])
    return min_aux


# This function updates the actual next scheduling events (i.e., taking into account if the buffer is empty)
def update_filtered_next_scheduling_event(i, filtered_next_scheduling_event, buffers):
    if is_buffer_empty(i, buffers) == True:
        filtered_next_scheduling_event[i] = positive_infinity
    else:
        filtered_next_scheduling_event[i] = next_scheduling_event[i]

# auxiliary printing function
def print_to_file(file_number):
    file_name_output = 'results_' + test_case_name + str(file_number) + '.json'
    f_output = open(file_name_output,'w')
    if file_number == -1:
        data = [node_of_issuance, N_nodes, comm_graph, rate_in, total_rate_in, base_delay, mana, total_mana, Qtotal, nu, max_messages, node_of_issuance, test_case_name]
    else:
        data = [time_of_beggining_of_new_round, messages_received, time_received]
    json.dump(data, f_output)
    f_output.close()

# ------------------------------------------------------
#
#                       MAIN
#
# ------------------------------------------------------

for message_number in range(1,max_messages+1):
    next_issuance_time = time_of_issuance[-1] + np.random.exponential(1/total_rate_in)                                                  # calculate the time of the next issuance event                  
    time_of_issuance.append(next_issuance_time)                                                                                         # append this time to a history list
    aux = np.random.uniform(0, 1)                                                                                                       # |\
    next_issuing_node = 0                                                                                                               # |\
    while aux > sum(rate_in[:next_issuing_node])/total_rate_in:                                                                         # | determines who issued the message
        next_issuing_node = next_issuing_node + 1                                                                                       # |/
    next_issuing_node = next_issuing_node - 1                                                                                           # |/
    node_of_issuance.append(next_issuing_node)                                                                                          # |/

 #   print(message_number, "of", max_messages)
                                                                                                                                        # schedules, gossips and enqueues everything (in order) before 'next_issuance_time'
    while min(filtered_next_scheduling_event) < next_issuance_time or min_list_of_lists(time_to_be_enqueued) < next_issuance_time :     # while there is a non-issuance event (scheduling or enqueueing) before the next issuance
        if min(filtered_next_scheduling_event) < min_list_of_lists(time_to_be_enqueued):                                                # if the first non-issuance event is a scheduling one
            next_scheduling_node = np.argmin(filtered_next_scheduling_event)                                                            # checks who is the node that is supposed to schedule something
            time_now = min(filtered_next_scheduling_event)                                                                              # checks when is the node supposed to schedule something
            schedule_and_gossip(next_scheduling_node, time_now, last_queue_being_scheduled, deficits, buffers, messages_received, time_received, messages_to_be_enqueued, time_to_be_enqueued, next_scheduling_event)
            enqueue(time_now, time_to_be_enqueued, messages_to_be_enqueued, buffers, next_scheduling_event, node_of_issuance)           # this function is not supposed to do nothing here, check later
            for i in range(N_nodes):                                                                                                    # |\ update (real) next scheduling events
                update_filtered_next_scheduling_event(i, filtered_next_scheduling_event, buffers)                                       # |/
        else:                                                                                                                           # if the first non-issuance event is a enqueueing one
            enqueue_up_to = min([min(filtered_next_scheduling_event), next_issuance_time])                                              # |\ enqueue everything up to the next non-enqueueing event
            enqueue(enqueue_up_to, time_to_be_enqueued, messages_to_be_enqueued, buffers, next_scheduling_event, node_of_issuance)      # |/
            for i in range(N_nodes):                                                                                                    # |\ update (real) next scheduling events
                update_filtered_next_scheduling_event(i, filtered_next_scheduling_event, buffers)                                       # |/

                                                                                                                                        # next issuance at next_issuance_time from next_issuing node
    if is_buffer_empty(next_issuing_node, buffers) == True and next_scheduling_event[next_issuing_node] < next_issuance_time:           # |\ nothing is scheduled if there is nothing to be scheduled, so the next_scheduling_event should be postponed when the buffer is empty
        next_scheduling_event[next_issuing_node] = next_issuance_time                                                                   # |/
    for i in range(N_nodes):                                                                                                            # |\ 
        unknown_messages[i].append(message_number)                                                                                      # |/ a new message is unknown to everybody except to whoever issued it
    unknown_messages[next_issuing_node].pop(-1)                                                                                         # |/
    buffers[next_issuing_node][next_issuing_node].append(message_number)                                                                # updates the issuer buffer
    messages_received[next_issuing_node].append(message_number)                                                                         # |\ updates the history of the issuer
    time_received[next_issuing_node].append(next_issuance_time)                                                                         # |/
    filtered_next_scheduling_event[next_issuing_node] = next_scheduling_event[next_issuing_node]                                        # update (real) next scheduling events

    if message_number % 10_000 == 0:    
        print_to_file(message_number // 10_000)
        time_of_beggining_of_new_round = [[] for i in range(N_nodes)] 
        messages_received = [[] for i in range(N_nodes)]        
        time_received = [[] for i in range(N_nodes)]        
    print_to_file(-1)

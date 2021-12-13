import json

for gran in range(3):
    for delay in range(2):
        for top in range(3):
            test_case = str(gran+1) + str(delay+1) + str(top+1) + '.in'
            f = open(test_case,'w')
            data = [gran+1, delay+1, top+1]
            json.dump(data, f)
            f.close()


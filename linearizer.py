
import time
import random

CACHE = {}

def linearize(pop, number = 0):
    if number:
        return compute_bounded_plans(pop, number)
    else:
        return compute_plans(pop, set(), set([pop.init]))

def count_linearizations(pop):
    global CACHE
    CACHE = {}
    return count_plans(pop, set(), set([pop.init]))

def check_successor(pop, seen, successor):
    return set([item[0] for item in pop.network.in_edges(successor)]) <= seen

def compute_plans(pop, seen, possible):
    if 0 == len(possible):
        return [[]]

    #print "Call:\n Seen: %s\n Possible: %s\n\n" % (str(seen), str(possible))
    #time.sleep(1)

    plans = []

    for action in possible:

        new_possible = set()

        for successor in [item[1] for item in pop.network.out_edges(action)]:
            if check_successor(pop, seen | set([action]), successor):
                new_possible.add(successor)

        new_plans = compute_plans(pop, seen | set([action]), (possible - set([action])) | new_possible)
        plans.extend([[action] + item for item in new_plans])

    #print "Returning Plans: %s" % str(plans)
    #time.sleep(1)

    return plans

def count_plans(pop, seen, possible):
    global CACHE

    hash_val = '/'.join(sorted([str(hash(item)) for item in list(seen)]))

    if hash_val in CACHE:
        return CACHE[hash_val]

    if 0 == len(possible):
        return 1

    total = 0
    for action in possible:
        new_possible = set()
        for successor in [item[1] for item in pop.network.out_edges(action)]:
            if check_successor(pop, seen | set([action]), successor):
                new_possible.add(successor)

        total += count_plans(pop, seen | set([action]), (possible - set([action])) | new_possible)

    CACHE[hash_val] = total

    return total

def compute_bounded_plans(pop, bound):
    plans = []
    seen = set()
    while len(plans) < bound:
        new_plan = generate_random_plan(pop, set(), set([pop.init]))
        hash_val = ','.join([str(hash(item)) for item in new_plan])
        if hash_val not in seen:
            seen.add(hash_val)
            plans.append(new_plan)

    return plans

def generate_random_plan(pop, seen, possible):
    if 0 == len(possible):
        return []

    next_action = random.choice(list(possible))

    new_possible = set()

    for successor in [item[1] for item in pop.network.out_edges(next_action)]:
        if check_successor(pop, seen | set([next_action]), successor):
            new_possible.add(successor)

    return [next_action] + generate_random_plan(pop, seen | set([next_action]), (possible - set([next_action])) | new_possible)


import networkx as nx

from krrt.planning.strips.representation import parse_problem, Action
from krrt.planning import parse_output_FF

from pop import POP


def lift_POP(domain = 'domain.pddl', problem = 'prob.pddl', ffout = 'FF.out', serialized = False):

    plan = parse_output_FF(ffout)
    allF, allA, I, G = parse_problem(domain, problem)

    pop = POP()
    F = set()
    A = set()
    indices = {None: 99999} # Should be larger than any plan we need to deal with
    reverse_indices = {}
    index = 1

    # Init action
    init = Action(set(), I, set(), "init")
    pop.add_action(init)
    F |= init.adds
    A.add(init)
    indices[init] = 0
    reverse_indices[0] = init

    # Normal actions
    for act in plan.actions:
        a = allA[str(act)[1:-1]]
        if a in A:
            a = a.copy()
        pop.add_action(a)
        F |= a.adds | a.precond | a.dels
        A.add(a)
        indices[a] = index
        reverse_indices[index] = a
        index += 1

    # Goal action
    goal = Action(G, set(), set(), "goal")
    pop.add_action(goal)
    F |= goal.precond
    A.add(goal)
    indices[goal] = index
    reverse_indices[index] = goal

    pop.F = F
    pop.A = A
    pop.I = I
    pop.G = G

    # If a serialized plan was called for, make sure the actions are in their original order
    if serialized:
        for i in range(index):
            pop.link_actions(reverse_indices[i], reverse_indices[i+1], "serial")
        return pop

    adders = {}
    deleters = {}

    for f in F:
        adders[f] = set()
        deleters[f] = set()

    for a in A:
        for f in a.adds:
            adders[f].add(a)
        for f in a.dels:
            deleters[f].add(a)

    for act in A:
        for p in act.precond:
            # Find the earliest adder of p that isn't threatened
            dels_before = set(filter(lambda x: indices[x] < indices[act], deleters[p]))
            dels_after = (deleters[p] - dels_before) - set([act])

            latest_deleter = -1

            for deleter in dels_before:
                if indices[deleter] > latest_deleter:
                    latest_deleter = indices[deleter]

            assert 0 == len(dels_before) or latest_deleter > -1
            assert latest_deleter < indices[act]

            earliest_adder = None

            for adder in adders[p]:
                if (indices[adder] > latest_deleter) and (indices[adder] < indices[earliest_adder]):
                    earliest_adder = adder

            assert earliest_adder is not None
            assert indices[earliest_adder] < indices[act], "%s, %s, %s" % (str(indices[earliest_adder]), str(indices[act]), str(p))
            assert latest_deleter < indices[earliest_adder]

            # We now have an unthreatened adder of fluent p for action act
            #  - Add the causal link
            pop.link_actions(earliest_adder, act, p)

            #  - Forbid the threatening actions
            for deleter in dels_before:
                #pop.link_actions(deleter, earliest_adder, (earliest_adder, act, p))
                pop.link_actions(deleter, earliest_adder, "! %s" % str(p))

            for deleter in dels_after:
                #pop.link_actions(act, deleter, (adder, act, p))
                pop.link_actions(act, deleter, "! %s" % str(p))

    # Ensure an ordering of all actions after the initial state, and before the goal state
    #shortest_paths = nx.all_pairs_shortest_path_length(pop.network)
    for act in A:
        # We repeat this each time to avoid transitively required ordering constraints
        shortest_paths = nx.all_pairs_shortest_path_length(pop.network)

        if act not in shortest_paths[init]:
            pop.link_actions(init, act, "init")

        if goal not in shortest_paths[act]:
            pop.link_actions(act, goal, "goal")

    assert nx.is_directed_acyclic_graph(pop.network)

    return pop


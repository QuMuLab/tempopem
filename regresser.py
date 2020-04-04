
import networkx as nx

from krrt.planning.strips import progress_state, regress_state, is_applicable
from krrt.planning.strips.representation import Action

from linearizer import linearize
from pop import TemporalConstraint


def build_regression_list(pop):

    assert pop.init is not None
    assert pop.goal is not None

    # Compute the lower-bound network for the POP where
    #  edges exist if there is a lower bound between nodes
    #
    #    NOTE: This was removed since we are ruling out lower bounds of 0
    #
    #G = nx.DiGraph()
    #G.add_nodes_from(pop.network.nodes())
    #for n1 in pop.network:
    #    for n2 in pop.network[n1]:
    #        if pop.network.edge[n1][n2]['constraint'].l > 0:
    #            G.add_edge(n1, n2)
    #pop.lower_network = G


    # Build the set of potential forced orderings (i.e., where reversing the order could lead
    #  to a different precondition set)
    forced_candidates = {}
    reachability = nx.all_pairs_shortest_path(pop.network)
    for u in pop.network:
        forced_candidates[u] = set()
        for v in pop.network:
            if (u != v) and (v not in reachability[u]) and (u not in reachability[v]):
                # First 4 checks will be handled by the is_regressable stuff later on
                #if (u.adds & v.precond) or (u.adds & v.dels) or (u.precond & v.dels):
                if (u.adds & v.precond) and (not (u.adds & v.dels)) and (not (u.precond & v.dels)):
                    forced_candidates[u].add(v)

    #print "\n".join(["%s:%s" % (k,forced_candidates[k]) for k in forced_candidates.keys()])

    level = 0
    max_level = len(pop.network.nodes()) - 1
    suffixes = []
    going = True

    precset_mapping = {}
    apsp_mapping = {}

    consistent_suffix_mapping = {}
    suffix_hash_mapping = {}

    while going:

        print "Level %d of %d." % (level+1, max_level),
        current_suffixes = set()

        if 0 == level:

            goal_suffix = Suffix(pop, pop.goal)
            current_suffixes.add(goal_suffix)
            precset_mapping[goal_suffix] = set([PrecSet(pop.goal.precond, pop.goal)])
            (valid, apsp) = goal_suffix.temporally_consistent(pop.goal)
            assert valid
            apsp_mapping[goal_suffix] = {pop.goal: apsp}

        else:

            for suffix in suffixes[-1]:
                for action in suffix.addable_actions:

                    # Get the forced orderings that this action will be a part of
                    fo = [(action, other) for other in (forced_candidates[action] & suffix.actions)]
                    fo = []
                    suf_hash = ','.join([str(a) for a in sorted(map(id, suffix.actions | set([action])))] +
                                        [str(o) for o in sorted(map(str, suffix.forced_orderings + fo))])

                    if suf_hash not in suffix_hash_mapping:
                        new_suffix = suffix.copy(action, fo)
                        suffix_hash_mapping[suf_hash] = new_suffix
                    else:
                        new_suffix = suffix_hash_mapping[suf_hash]

                    if new_suffix not in consistent_suffix_mapping:
                        consistent_suffix_mapping[new_suffix] = {}
                        apsp_mapping[new_suffix] = {}

                    if action not in consistent_suffix_mapping[new_suffix]:
                        (is_consistent, apsp) = new_suffix.temporally_consistent(action)
                        consistent_suffix_mapping[new_suffix][action] = is_consistent
                        apsp_mapping[new_suffix][action] = apsp

                    if not consistent_suffix_mapping[new_suffix][action]:
                        continue

                    if new_suffix not in current_suffixes:
                        current_suffixes.add(new_suffix)
                        precset_mapping[new_suffix] = set()

                    for precset in precset_mapping[suffix]:
                        if is_applicable(precset.prec, action, regress=True):
                            precset_mapping[new_suffix].add(PrecSet(regress_state(precset.prec, action), action))

        suffixes.append(current_suffixes)

        print "(|Suffixes|, |Precs|) = (%s, %s)" % (str(len(suffixes[-1])), str(sum([len(precset_mapping[suf]) for suf in suffixes[-1]])))

        level += 1

        if level == max_level:
            going = False

    return (suffixes, precset_mapping, apsp_mapping)


class Suffix(object):
    def __init__(self, pop, goal = None):
        self.actions = set()
        self.forced_orderings = []

        self.pop = pop
        self.addable_actions = set()
        self.forall_constraints = []
        self.forall_constraint_mapping = {}
        self.goal_estimates = {}
        self.nodes_of_interest = set()

        if goal:
            self.actions.add(goal)
            self.compute_hash_val()
            self.compute_LHS(goal)

    def copy(self, action, new_fo):
        # Do the housework for the suffix data structures
        new = Suffix(self.pop)
        new.actions = self.actions.copy()
        new.addable_actions = self.addable_actions.copy()
        new.forced_orderings = self.forced_orderings[:] + new_fo

        new.addable_actions.remove(action)
        new.actions.add(action)
        new.compute_hash_val()

        # Although the computation uses action (to be efficient in finding the fringe),
        #  it is unique according to the set of actions in the right hand side.
        new.compute_LHS(action)

        return new

    def compute_LHS(self, act):
        # Deal with the fringe movement
        # NOTE: See comment at the top of the file on the removal of lower_network
        #new_fringe = set([item[0] for item in self.pop.lower_network.in_edges(act)])
        new_fringe = set([item[0] for item in self.pop.network.in_edges(act)])

        for pre in new_fringe:

            assert pre not in self.actions

            # NOTE: See comment at the top of the file on the removal of lower_network
            #post = set([item[1] for item in self.pop.lower_network.out_edges(pre)])
            post = set([item[1] for item in self.pop.network.out_edges(pre)])
            if 0 == len(post - self.actions):
                self.addable_actions.add(pre)

        # Create the temporal network for this suffix split
        self.network = nx.DiGraph()

        # Add the nodes to the right of partition
        right_nodes = self.actions
        self.left_nodes = set()
        self.follow_forcers = set()
        self.start_forall_nodes = set()
        self.unstarted_forall_constraints = set()
        self.network.add_nodes_from(right_nodes)

        # Add the nodes to the left of the partition that have constraints
        for n in right_nodes:
            for (pre, _) in self.pop.network.in_edges(n):
                if 'constraint' in self.pop.network.edge[pre][n]:

                    constraint = self.pop.network.edge[pre][n]['constraint']

                    # If it is a forced follow, then record the constraint and leave out the starting node
                    if constraint.forced == TemporalConstraint.FORCE_FOLLOW:
                        self.follow_forcers.add(constraint)

                    elif (pre not in self.network) and (not constraint.is_simple):
                        self.network.add_node(pre)
                        self.left_nodes.add(pre)

        # Add all of the edges entering the right nodes
        for n in right_nodes:

            # Keep the right node around if it is being forced (we'll need to check the bounds at runtime)
            if n in self.pop.follow_constraints_rhs_map:
                self.nodes_of_interest.add(n)

            for (pre, _) in self.pop.network.in_edges(n):
                if pre in self.network:

                    # Check if it's just an ordering constraint
                    if 'constraint' not in self.pop.network.edge[pre][n]:
                        self.network.add_weighted_edges_from([(n, pre, -1 * TemporalConstraint.epsilon)])

                    # Otherwise it must be a temporal constraint
                    else:
                        constraint = self.pop.network.edge[pre][n]['constraint']

                        # We don't want the edges if it is a forced follow with the chance of the start not happening
                        if (constraint.forced != TemporalConstraint.FORCE_FOLLOW) or (pre in right_nodes):
                            self.network.add_edges_from(constraint.edges())

                        # Handle the forall constraint separately
                        if constraint.enforce == TemporalConstraint.ENFORCE_FORALL:

                            # Split if pre is a left-node so the forall bounds propagate
                            if pre in self.left_nodes:
                                new_action = Action(pre.precond, pre.adds, pre.dels, "c_%s" % str(pre)[1:-1])
                                self.start_forall_nodes.add(new_action)
                                self.network.add_node(new_action)

                                split_cons = TemporalConstraint(new_action, pre)
                                copied_cons = constraint.copy(new_action, n)
                                self.network.add_edge(new_action, pre, constraint=split_cons)
                                self.network.add_edge(new_action, n, constraint=copied_cons)

                                self.network.add_edges_from(split_cons.edges())
                                self.network.add_edges_from(copied_cons.edges())

                                if 'forall_copies' not in dir(pre):
                                    pre.forall_copies = []
                                pre.forall_copies.append(new_action)

                            # Otherwise we prep the suffix to process itself later if 'a' is executed
                            else:
                                if n not in self.forall_constraint_mapping:
                                    self.forall_constraint_mapping[n] = []
                                self.forall_constraint_mapping[n].append(constraint)
                                self.forall_constraints.append(constraint)
                                self.unstarted_forall_constraints.add(constraint)
                                self.nodes_of_interest.add(n)


        # Add the forced ordering constraints
        #  Note: The order is switched since the edge for lower bounds goes from the later event to the earlier
        for (v,u) in self.forced_orderings:
            if self.network.has_edge(u, v):
                self.network[u][v]['weight'] = min(self.network[u][v]['weight'], -1 * TemporalConstraint.epsilon)
            else:
                self.network.add_weighted_edges_from([(u, v, -1 * TemporalConstraint.epsilon)])


    def recheck_temporal_viability(self, act, lhs_timings, follow_constraints):

        G = self.network
        old_edges = []
        rem_edges = []
        assert act in G.nodes(), str(act)

        def modify_edge(u,v,w):
            if G.has_edge(u,v):
                old_edges.append((u,v,G[u][v]['weight']))
                G[u][v]['weight'] = w
            else:
                rem_edges.append((u,v))
                G.add_weighted_edges_from([(u,v,w)])

        def modify_edge_min(u,v,w):
            if G.has_edge(u,v):
                old_edges.append((u,v,G[u][v]['weight']))
                G[u][v]['weight'] = min(G[u][v]['weight'], w)
            else:
                rem_edges.append((u,v))
                G.add_weighted_edges_from([(u,v,w)])

        # Add constraints to place the candidate node at the start
        for n in self.actions:
            if act is not n:
                modify_edge_min(n,act,-1*TemporalConstraint.epsilon)

        for n in self.left_nodes:
            modify_edge_min(act,n,-1*TemporalConstraint.epsilon)

            # Lock in the timings for the previously executed actions
            modify_edge(self.pop.init, n, lhs_timings[n])
            modify_edge(n, self.pop.init, -1 * lhs_timings[n])

        # Add the force follow constraint time bounds
        for (a,l,u) in follow_constraints:
            modify_edge_min(self.pop.init, a, u)
            modify_edge_min(a, self.pop.init, -1 * l)

        # We need to re-encode things since we get a numpy matrix back
        M = nx.floyd_warshall_numpy(G)
        m = dict(zip(G.nodes(), range(len(G.nodes()))))

        # Reset the edges
        for (s,t,w) in reversed(old_edges):
            G[s][t]['weight'] = w
        for (s,t) in rem_edges:
            G.remove_edge(s,t)

        # Make sure there is no forced concurrency or negative cycles
        for i in range(G.number_of_nodes()):
            for j in range(G.number_of_nodes()):
                if i == j:
                    if M[i,j] < 0:
                        return (False, None)
                else:
                    if (0 == M[i,j]) and (0 == M[j,i]):
                        return (False, None)

        return (True, [-1 * M[m[act], m[self.pop.init]], M[m[self.pop.init], m[act]]])

    def temporally_consistent(self, act):

        G = self.network
        old_edges = []
        rem_edges = []
        assert act in G.nodes(), str(act)

        # Add constraints to place the candidate node at the start
        for n in self.actions:
            assert n in G
            if act is not n:
                if G.has_edge(n, act):
                    old_edges.append((n,act,G[n][act]['weight']))
                    G[n][act]['weight'] = min(G[n][act]['weight'], -1 * TemporalConstraint.epsilon)
                else:
                    rem_edges.append((n,act))
                    G.add_weighted_edges_from([(n, act, -1 * TemporalConstraint.epsilon)])

        for n in self.left_nodes | self.start_forall_nodes:
            assert n in G
            if G.has_edge(act, n):
                old_edges.append((act,n,G[act][n]['weight']))
                G[act][n]['weight'] = min(G[act][n]['weight'], -1 * TemporalConstraint.epsilon)
            else:
                rem_edges.append((act,n))
                G.add_weighted_edges_from([(act, n, -1 * TemporalConstraint.epsilon)])

        # We need to re-encode things since we get a numpy matrix back
        M = nx.floyd_warshall_numpy(G)
        m = dict(zip(G.nodes(), range(len(G.nodes()))))

        # Reset the edges
        for (s,t,w) in old_edges:
            G[s][t]['weight'] = w
        for (s,t) in rem_edges:
            G.remove_edge(s,t)

        # Make sure there is no forced concurrency or negative cycles
        for i in range(G.number_of_nodes()):
            for j in range(G.number_of_nodes()):
                if i == j:
                    if M[i,j] < 0:
                        return (False, None)
                else:
                    if (0 == M[i,j]) and (0 == M[j,i]):
                        return (False, None)


        apsp = {}
        for n1 in self.left_nodes | self.start_forall_nodes | set([act]):
            apsp[n1] = {}
            for n2 in self.left_nodes | self.nodes_of_interest | self.start_forall_nodes | set([act]):
                if n1 != n2:
                    apsp[n1][n2] = [-1 * M[m[n2], m[n1]],
                                          M[m[n1], m[n2]]]

        # Store the lower bound between the candidate action and the goal (for heuristic sake)
        self.goal_estimates[act] = -1 * M[m[self.pop.goal], m[act]]

        return (True, apsp)

    def compute_hash_val(self):
        self.hash_val = ','.join([str(a) for a in sorted(map(id, self.actions))] + [str(o) for o in sorted(map(str, self.forced_orderings))])

    def __hash__(self):
        return self.hash_val.__hash__()

    def __str__(self):
        return "Actions: %s" % self.hash_val

    def __repr__(self):
        return self.__str__()

    def __cmp__(self, other):
        return self.__hash__() == other.__hash__()

    def __eq__(self, other):
        return self.__cmp__(other)

    def __neq__(self, other):
        return not self.__cmp__(other)

class PrecSet(object):
    def __init__(self, prec, candidate):
        self.prec = prec
        self.candidate = candidate
        self.prec_val = ','.join(sorted([str(p) for p in prec]))
        self.hash_val = hash(str(self))

    def __hash__(self):
        return self.hash_val

    def __str__(self):
        return "%s: %s" % (str(self.candidate), self.prec_val)

    def __repr__(self):
        return self.__str__()

    def __cmp__(self, other):
        return self.__hash__() == other.__hash__()

    def __eq__(self, other):
        return self.__cmp__(other)

    def __neq__(self, other):
        return not self.__cmp__(other)

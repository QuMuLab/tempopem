
from timeit import Timer
from functools import partial
from operator import itemgetter
from random import shuffle

from krrt.utils import get_lines

from pop import TemporalConstraint

VERBOSE = False

class TempPolicy(object):
    def __init__(self, sgpol, apsp, P):

        self.policy = sgpol
        self.apsp = apsp
        self.pop = P
        self.mode = 'us'

        self.follow_constraints = P.follow_constraints
        self.follow_mapping = {}
        self.follow_unmapping = {}
        for c in self.follow_constraints:
            if c.s not in self.follow_mapping:
                self.follow_mapping[c.s] = []
            self.follow_mapping[c.s].append(c)
            if c.t not in self.follow_unmapping:
                self.follow_unmapping[c.t] = []
            self.follow_unmapping[c.t].append(c)

        self.reset()

    def reset(self):
        self.replan_count = 0
        self.last_suffix = None
        self.action_times = {}
        self.trace = []
        self.last_time = -1 * TemporalConstraint.epsilon
        self.active_follow_constraints = set()
        self.active_follow_indices = {}
        #self.agent_free = True
        self.add_action(0.0, self.pop.init)

        # Hard coded schedule for a static stn dispatcher
        self.stn_plan = [
            [self.pop.A_map['init'], 0.000000, 0.000000],
            [self.pop.A_map['wakeup'], 420.000000, 420.000000],
            [self.pop.A_map['serve_breakfast'], 30.000000, 30.000000],
            [self.pop.A_map['check_full'], 15.000005, 15.000005],
            [self.pop.A_map['startA_drive_kids_school'], 29.999995, 29.999995],
            [self.pop.A_map['endA_drive_kids_school'], 30.000000, 30.000000],
            [self.pop.A_map['startA_drive_mall'], 82.499975, 82.499975],
            [self.pop.A_map['endA_drive_mall'], 20.000000, 20.000000],
            [self.pop.A_map['check_at_mall'], 41.249988, 41.249988],
            [self.pop.A_map['startA_get_groceries'], 20.624999, 20.624999],
            [self.pop.A_map['endA_get_groceries'], 60.000000, 60.000000],
            [self.pop.A_map['startA_watch_movie'], 10.312504, 10.312504],
            [self.pop.A_map['endA_watch_movie'], 95.156247, 95.156247],
            [self.pop.A_map['startA_drive_home'], 2.578134, 2.578134],
            [self.pop.A_map['endA_drive_home'], 20.000000, 20.000000],
            [self.pop.A_map['startA_do_laundry'], 1.289067, 1.289067],
            [self.pop.A_map['startA_read_book'], 0.644538, 0.644538],
            [self.pop.A_map['endA_do_laundry'], 29.999990, 29.999990],
            [self.pop.A_map['check_at_home'], 0.322269, 0.322269],
            [self.pop.A_map['endA_read_book'], 0.161140, 0.161140],
            [self.pop.A_map['startA_drive_school'], 0.080575, 0.080575],
            [self.pop.A_map['endA_drive_school'], 20.000000, 20.000000],
            [self.pop.A_map['startA_drive_kids_home'], 0.040292, 0.040292],
            [self.pop.A_map['endA_drive_kids_home'], 30.000000, 30.000000],
            [self.pop.A_map['startA_clean_kitchen'], 80.020136, 80.020136],
            [self.pop.A_map['endA_clean_kitchen'], 20.000000, 20.000000],
            [self.pop.A_map['check_clean_kitchen'], 30.010073, 30.010073],
            [self.pop.A_map['startA_cook_meal'], 25.005032, 25.005032],
            [self.pop.A_map['endA_cook_meal'], 17.502516, 17.502516],
            [self.pop.A_map['serve_meal'], 3.751268, 3.751268],
            [self.pop.A_map['goto_sleep'], 121.875634, 121.875634]
        ]

    def get_action(self, time, state, metric=None):
        assert time >= self.last_time

        if 'stn' == self.mode:
            if 0 == len(self.stn_plan):
                return [self.pop.goal, time, time]
            else:
                return self.stn_plan.pop(0)

        # Fetch all of the semantically relevant suffixes, and sort them based on quality
        options = []
        #if self.agent_free:
        #    self.policy.evaluate(state | set([self.pop.free_fluent]) , options)
        #else:
        #    self.policy.evaluate(state, options)
        self.policy.evaluate(state, options)
        shuffle(options) # Shuffle to randomly distribute tied contexts
        options.sort(key=itemgetter(2))

        if VERBOSE:
            print "\nCausally viable options:\n"
            print "\n".join(["%s: %s" % (str(o[0]), str(o[2])) for o in options])
            print

        if 'timings' == metric:
            time_pre = 0.0
            time_unpre = 0.0
        elif 'viable_counts' == metric:
            causal_count = len(options)
            temporal_count = len(filter(lambda x: x[0], [self.temporally_valid(time, act, suf, False) for (act, suf, cost) in options]))
            checked_count = 0

        # Iterate through until we find a temporally viable suffix
        for (act, suf, cost) in options:

            (valid, result) = self.temporally_valid(time, act, suf, False)

            if 'timings' == metric:
                t = Timer(partial(self.temporally_valid, time, act, suf, False))
                time_pre += min(t.repeat(3, 100))

                t = Timer(partial(self.temporally_valid, time, act, suf, True))
                time_unpre += min(t.repeat(3, 100))

                result = (result, time_pre, time_unpre)

            elif 'viable_counts' == metric:
                checked_count += 1
                result = (result, causal_count, temporal_count, checked_count)

            if valid:
                if 'seren' != self.mode or act not in self.action_times:
                    if VERBOSE:
                        print "\nTemporally Succeeded Suffix:"
                        print "Action: %s" % str(act)
                        print "Suffix: %s" % str(sorted(map(str, suf.actions)))
                        print "Suffix orderings: %s" % str(suf.forced_orderings)
                        print "Cost: %s" % str(cost)
                        print "Result: %s" % str(result)
                    return result

            elif VERBOSE:
                print "\nTemporally Failed Suffix:"
                print "Action: %s" % str(act)
                print "State: %s" % str(state)
                print "Suffix: %s" % str(sorted(map(str, suf.actions)))
                print "Suffix orderings: %s" % str(suf.forced_orderings)
                print "Cost: %s" % str(cost)
                print "Result: %s" % str(result)


        return None

    def add_action(self, time, action):
        assert time >= self.last_time
        self.last_time = time
        self.trace.append((action, time))
        if action not in self.action_times:
            self.action_times[action] = []
            # If this is the first occurrence, we need to make sure the copy is included
            if 'forall_copies' in dir(action):
                for copy in action.forall_copies:
                    self.action_times[copy] = [time]
        self.action_times[action].append(time)

        # Keep track if the agent is free
        #if 'startA_' == action.operator[:7]:
        #    self.agent_free = False

        #if 'endA_' == action.operator[:5]:
        #    self.agent_free = True

        # ########################### #
        # Handle the forced following #
        # ########################### #

        # Reset the satisfied ones
        for cons in self.follow_unmapping.get(action, []):
            if cons in self.active_follow_constraints:
                self.active_follow_constraints.remove(cons)
                del self.active_follow_indices[cons]


        # Add the newly activated ones
        for cons in self.follow_mapping.get(action, []):
            self.active_follow_constraints.add(cons)
            self.active_follow_indices[cons] = len(self.action_times[action]) - 1

    def temporally_valid(self, now, action, suffix, recompute=False):

        if self.apsp[suffix][action] is None:
            return (False, "Action not in the apsp: %s" % str(action))

        # First check that all of the events in the past have happened
        for a in suffix.left_nodes:
            if a not in self.action_times:
                return (False, "Missing a left-node action: %s" % str(a))

        # Next check if the suffix contains everything that must (temporally)
        #  occur in the future due to the forced following constraints
        for cons in self.active_follow_constraints:
            if cons.t not in suffix.actions:
                return (False, "Missing a forced follow action in the suffix: %s" % str(cons.t))


        # ##############
        #
        # ForAll Case
        #
        # ############
        #
        #   This arises when we have a forall constraint entirely within the RHS
        #  and we haven't dealt with splitting the node. It only needs to be split
        #  if a (from a->b) was executed and it hasn't been split yet.
        #
        # ############
        made_change = False
        for cons in filter(lambda x: x.s in self.action_times, suffix.unstarted_forall_constraints):

            made_change = True

            suffix.unstarted_forall_constraints.remove(cons)
            new_action = Action(cons.s.precond, cons.s.adds, cons.s.dels, "c_%s" % str(cons.s)[1:-1])
            self.action_times[new_action] = [self.action_times[cons.s][0]]

            suffix.start_forall_nodes.add(new_action)
            suffix.network.add_node(new_action)
            suffix.network.add_edge(new_action, cons.s, constraint=TemporalConstraint(new_action, cons.s))
            suffix.network.add_edge(new_action, cons.t, constraint=cons.copy())

        if made_change:
            (valid, apsp) = suffix.temporally_consistent(action)
            if valid:
                self.apsp[suffix][action] = apsp
            else:
                self.apsp[suffix][action] = None

        # #################


        # Next grab the past events and sort them based on time
        past = [(a, self.action_times[a][-1]) for a in suffix.left_nodes] + \
               [(a, self.action_times[a][0]) for a in suffix.start_forall_nodes]
        past.sort(key=itemgetter(1))

        # Finally, project the temporal windows forward
        windows = {}
        for a in suffix.nodes_of_interest | suffix.left_nodes | suffix.start_forall_nodes | set([action]):
            windows[a] = [0, float('inf')]


        if recompute:
            follow_constraints = []
            for cons in self.active_follow_constraints:
                follow_constraints.append((cons.t,
                                           self.action_times[cons.s][-1] + cons.l,
                                           self.action_times[cons.s][self.active_follow_indices[cons]] + cons.u))

            lhs_timings = dict([(a,self.action_times[a][-1]) for a in suffix.left_nodes])
            (valid, new_bounds) = suffix.recheck_temporal_viability(action, lhs_timings, follow_constraints)

            if valid:
                windows[action][0] = max(windows[action][0], new_bounds[0])
                windows[action][1] = min(windows[action][1], new_bounds[1])
                # Do one final check for the update
                if now > windows[action][1]:
                    return (False, "Too much time has gone by")
                if windows[action][0] > windows[action][1]:
                    return (False, "Candidate action window is reduced to empty: %s [%f, %f]" % (action, windows[action][0], windows[action][1]))
            else:
                return (False, "Failed to re-establish temporal consistency with forced follow constraints:\n%s\n%s" % \
                        ("\n".join(["(%s,%s): %s" % (c.s, c.t, c.label) for c in self.active_follow_constraints]),
                         "\n".join(["%s in [%f,%f]" % (c[0], c[1], c[2]) for c in follow_constraints])))

            # Otherwise, return the candidate action and time bounds
            return (True, [action, max(0, windows[action][0] - now), windows[action][1] - now])


        for (a, ta) in past:
            # If it is out of the bounds, then it isn't temporally valid
            if (ta < windows[a][0]) or (ta > windows[a][1]):
                return (False, "Past temporal window for %s@%f violated: [%f,%f]" % (str(a), ta, windows[a][0], windows[a][1]))

            # Otherwise, we propagate the temporal windows
            for (a2,ta2) in past:
                if (a != a2) and (ta2 >= ta):
                    windows[a2][0] = max(windows[a2][0], ta + self.apsp[suffix][action][a][a2][0])
                    windows[a2][1] = min(windows[a2][1], ta + self.apsp[suffix][action][a][a2][1])
                    if windows[a2][0] > windows[a2][1]:
                        return (False, "Bad temporal window on %s: [%f,%f]" % (a2, windows[a2][0], windows[a2][1]))

            for a2 in suffix.nodes_of_interest:
                windows[a2][0] = max(windows[a2][0], ta + self.apsp[suffix][action][a][a2][0])
                windows[a2][1] = min(windows[a2][1], ta + self.apsp[suffix][action][a][a2][1])
                if windows[a2][0] > windows[a2][1]:
                    return (False, "Bad temporal window on %s: [%f,%f]" % (a2, windows[a2][0], windows[a2][1]))

            windows[action][0] = max(windows[action][0], ta + self.apsp[suffix][action][a][action][0])
            windows[action][1] = min(windows[action][1], ta + self.apsp[suffix][action][a][action][1])
            if windows[action][0] > windows[action][1]:
                return (False, "Bad temporal window on %s: [%f,%f]" % (action, windows[action][0], windows[action][1]))

        # Check to make sure that the active forced following constraints do not tighten
        #  any of the windows on the RHS forced nodes
        rerun_apsp = False
        for cons in self.active_follow_constraints:
            # Handle the candidate action separately
            if cons.t == action:
                windows[action][0] = max(windows[action][0], self.action_times[cons.s][-1] + cons.l)
                windows[action][1] = min(windows[action][1], self.action_times[cons.s][self.active_follow_indices[cons]] + cons.u)

            else:
                # Check for violated lower bound
                if (self.action_times[cons.s][-1] + cons.l) > windows[cons.t][0]:
                    rerun_apsp = True

                # Check for violated upper bound
                if (self.action_times[cons.s][self.active_follow_indices[cons]] + cons.u) < windows[cons.t][1]:
                    rerun_apsp = True

        # If too much time has gone by, return False
        if now > windows[action][1]:
            return (False, "Too much time has gone by")

        # Finally, check to make sure the execution window wasn't squeezed out
        if windows[action][0] > windows[action][1]:
            return (False, "Candidate action window is reduced to empty: %s [%f, %f]" % (action, windows[action][0], windows[action][1]))

        # Re-run the apsp if we have future constraints that could potentially tighten things
        if rerun_apsp:

            if VERBOSE:
                print "\n\nResorting to re-running the apsp for the forward constraints."

            follow_constraints = []
            for cons in self.active_follow_constraints:
                follow_constraints.append((cons.t,
                                           self.action_times[cons.s][-1] + cons.l,
                                           self.action_times[cons.s][self.active_follow_indices[cons]] + cons.u))

            lhs_timings = dict([(a,self.action_times[a][-1]) for a in suffix.left_nodes])
            (valid, new_bounds) = suffix.recheck_temporal_viability(action, lhs_timings, follow_constraints)

            if valid:
                windows[action][0] = max(windows[action][0], new_bounds[0])
                windows[action][1] = min(windows[action][1], new_bounds[1])
                # Do one final check for the update
                if now > windows[action][1]:
                    return (False, "Too much time has gone by: now / lb / ub = %f / %f / %f" % (now, windows[action][0], windows[action][1]))
                if windows[action][0] > windows[action][1]:
                    return (False, "Candidate action window is reduced to empty: %s [%f, %f]" % (action, windows[action][0], windows[action][1]))
            else:
                return (False, "Failed to re-establish temporal consistency with forced follow constraints:\n%s\n%s" % \
                        ("\n".join(["(%s,%s): %s" % (c.s, c.t, c.label) for c in self.active_follow_constraints]),
                         "\n".join(["%s in [%f,%f]" % (c[0], c[1], c[2]) for c in follow_constraints])))

        # Otherwise, return the candidate action and time bounds (after recording if a replan was required)
        if not self.check_suffix_follows(suffix, action):
            self.replan_count += 1

        return (True, [action, max(0, windows[action][0] - now), windows[action][1] - now])

        # Maybe only need to check the projected windows of the LHS onto 'action'
        #   ...if so, this should be a theorem that is proved, and we can forget
        #   storing most of apsp
        #
        #   ...as it turns out, this isn't possible. We need to keep the projection
        #   going for all of the events on the LHS. An example to demonstrate:
        #
        #   LHS: {1,2}   RHS: {3}   Candidate: 0
        #   Edges:
        #     (1,3): [6,6]
        #     (2,3): [2,4]
        #     (1,0): [0,inf] <-- Candidate edge
        #     (2,0): [0,inf] <-- Candidate edge
        #
        #   Computed Edges:
        #     (1,3): [6,6]
        #     (1,2): [2,4]
        #     (1,0): [2,6]
        #     (2,3): [2,4]
        #     (2,0): [0,4]
        #     (0,3): [0,4]
        #
        #   Bad sitation:
        #     t(1) = 4
        #     t(2) = 5
        #
        #   Reasoning:
        #      The timing violates the (1,2) edge, but allows for 0 any time
        #     in the [6,9] range. Even though the window for 0 is non-empty,
        #     action 3 will never work because of edges (1,3) and (2,3).
        #


    def check_suffix_follows(self, suf, act):
        # NOTE: Comment out this line to improve efficiency.
        #        It is only required for experiment 8.
        # return True

        if self.last_suffix is None:
            self.last_suffix = suf
            return True

        follows = (self.last_suffix.actions >= suf.actions) and \
                  (1 == len(self.last_suffix.actions - suf.actions))

        self.last_suffix = suf

        return follows



def example0():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    g1 = Fluent('g1')
    g2 = Fluent('g2')

    # Actions
    INIT = Action(set(), set([p1, p2]), set(), "init")
    GOAL = Action(set([g1, g2]), set(), set(), "goal")
    a1 = Action(set([p1]), set([g1]), set(), "a1")
    a2 = Action(set([p2]), set([g2]), set(), "a2")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)

    pop.link_actions(INIT, a1, p1)
    pop.link_actions(INIT, a2, p2)
    pop.link_actions(a1, GOAL, g1)
    pop.link_actions(a2, GOAL, g2)

    return pop

def example1():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    p3 = Fluent('p3')
    g1 = Fluent('g1')
    g2 = Fluent('g2')
    g3 = Fluent('g3')

    # Actions
    INIT = Action(set(), set([p1, p2, p3]), set(), "init")
    GOAL = Action(set([g1, g2, g3]), set(), set(), "goal")
    a1 = Action(set([p1]), set([g1]), set(), "a1")
    a2 = Action(set([p2]), set([g2]), set(), "a2")
    a3 = Action(set([p3]), set([g3]), set(), "a3")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)
    pop.add_action(a3)

    pop.link_actions(INIT, a1, p1)
    pop.link_actions(INIT, a2, p2)
    pop.link_actions(INIT, a3, p3)
    pop.link_actions(a1, GOAL, g1)
    pop.link_actions(a2, GOAL, g2)
    pop.link_actions(a3, GOAL, g3)

    return pop

def example2():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    g1 = Fluent('g1')
    g2 = Fluent('g2')

    # Actions
    INIT = Action(set(), set([p1]), set(), "init")
    GOAL = Action(set([g1, g2]), set(), set(), "goal")
    a1 = Action(set([p1]), set([p2,g2]), set(), "a1")
    a2 = Action(set([p2]), set([g1]), set(), "a2")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)

    pop.link_actions(INIT, a1, p1)
    pop.link_actions(a1, a2, p2)
    pop.link_actions(a1, GOAL, g2)
    pop.link_actions(a2, GOAL, g1)

    return pop

def example3():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    p3 = Fluent('p3')
    g = Fluent('g')

    # Actions
    INIT = Action(set(), set([p1]), set(), "init")
    GOAL = Action(set([g]), set(), set(), "goal")
    a1 = Action(set([p1]), set([p2]), set(), "a1")
    a2 = Action(set([p2]), set([p3]), set(), "a2")
    a3 = Action(set([p3]), set([g]), set(), "a3")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)
    pop.add_action(a3)

    pop.link_actions(INIT, a1, p1)
    pop.link_actions(a1, a2, p2)
    pop.link_actions(a2, a3, p3)
    pop.link_actions(a3, GOAL, g)

    return pop

def example4():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    p3 = Fluent('p3')
    g2 = Fluent('g2')
    g3 = Fluent('g3')

    # Actions
    INIT = Action(set(), set([p1, p3]), set(), "init")
    GOAL = Action(set([g2, g3]), set(), set(), "goal")
    a1 = Action(set([p1]), set([p2]), set(), "a1")
    a2 = Action(set([p2]), set([g2]), set(), "a2")
    a3 = Action(set([p3]), set([g3]), set(), "a3")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)
    pop.add_action(a3)

    pop.link_actions(INIT, a1, p1)
    pop.link_actions(INIT, a3, p3)
    pop.link_actions(a1, a2, p2)
    pop.link_actions(a2, GOAL, g2)
    pop.link_actions(a3, GOAL, g3)

    return pop

def example5():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    p31 = Fluent('p31')
    p32 = Fluent('p32')
    p4 = Fluent('p4')
    p5 = Fluent('p5')
    g1 = Fluent('g1')
    g2 = Fluent('g2')

    # Actions
    INIT = Action(set(), set([p1, p2]), set(), "init")
    GOAL = Action(set([g1, g2]), set(), set(), "goal")
    a1 = Action(set([p1]), set([p31]), set(), "a1")
    a2 = Action(set([p2]), set([p32]), set(), "a2")
    a3 = Action(set([p31,p32]), set([p4,p5]), set(), "a3")
    a4 = Action(set([p4]), set([g1]), set(), "a4")
    a5 = Action(set([p5]), set([g2]), set(), "a5")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)
    pop.add_action(a3)
    pop.add_action(a4)
    pop.add_action(a5)

    pop.link_actions(INIT, a1, p1)
    pop.link_actions(INIT, a2, p2)
    pop.link_actions(a1, a3, p31)
    pop.link_actions(a2, a3, p32)
    pop.link_actions(a3, a4, p4)
    pop.link_actions(a3, a5, p5)
    pop.link_actions(a4, GOAL, g1)
    pop.link_actions(a5, GOAL, g2)

    return pop

def example6():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    p3 = Fluent('p3')
    p41 = Fluent('p41')
    p42 = Fluent('p42')
    g1 = Fluent('g1')
    g2 = Fluent('g2')

    # Actions
    INIT = Action(set(), set([p1, p3]), set(), "init")
    GOAL = Action(set([g1, g2]), set(), set(), "goal")
    a1 = Action(set([p1]), set([p2,p41]), set(), "a1")
    a2 = Action(set([p2]), set([g1]), set(), "a2")
    a3 = Action(set([p3]), set([p42]), set(), "a3")
    a4 = Action(set([p41,p42]), set([g2]), set(), "a4")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)
    pop.add_action(a3)
    pop.add_action(a4)

    pop.link_actions(INIT, a1, p1)
    pop.link_actions(INIT, a3, p3)
    pop.link_actions(a1, a2, p2)
    pop.link_actions(a1, a4, p41)
    pop.link_actions(a3, a4, p42)
    pop.link_actions(a2, GOAL, g1)
    pop.link_actions(a4, GOAL, g2)

    return pop

def example7():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    p3 = Fluent('p3')
    g1 = Fluent('g1')
    g2 = Fluent('g2')

    # Actions
    INIT = Action(set(), set([p1, p3]), set(), "init")
    GOAL = Action(set([g1, g2]), set(), set(), "goal")
    a1 = Action(set([p1]), set([p2]), set(), "a1")
    a2 = Action(set([p2]), set([g1]), set(), "a2")
    a3 = Action(set([p3]), set([p2,g2]), set(), "a3")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)
    pop.add_action(a3)

    pop.link_actions(INIT, a1, p1)
    pop.link_actions(INIT, a3, p3)
    pop.link_actions(a1, a2, p2)
    pop.link_actions(a2, GOAL, g1)
    pop.link_actions(a3, GOAL, g2)

    return pop

def example8():
    from krrt.planning.strips.representation import Action, Fluent

    # Fluents
    p1 = Fluent('p1')
    p2 = Fluent('p2')
    p3 = Fluent('p3')
    p4 = Fluent('p4')
    g = Fluent('g')

    # Actions
    INIT = Action(set(), set([p4]), set(), "init")
    GOAL = Action(set([g]), set(), set(), "goal")
    a1 = Action(set([p1,p2,p3]), set([g]), set(), "a1")
    a2 = Action(set([p1,p4]), set([p2,p3]), set(), "a2")
    a3 = Action(set([p2]), set([p1,p4]), set(), "a3")
    a4 = Action(set([p3]), set([p2]), set(), "a4")
    a5 = Action(set([p4]), set([p3]), set(), "a5")

    # POP
    pop = POP()
    pop.add_action(INIT)
    pop.add_action(GOAL)
    pop.add_action(a1)
    pop.add_action(a2)
    pop.add_action(a3)
    pop.add_action(a4)
    pop.add_action(a5)

    pop.link_actions(INIT, a5, p4)
    pop.link_actions(a5, a4, p3)
    pop.link_actions(a4, a3, p2)
    pop.link_actions(a3, a2, p1)
    pop.link_actions(a3, a2, p4)
    pop.link_actions(a3, a1, p1)
    pop.link_actions(a2, a1, p2)
    pop.link_actions(a2, a1, p3)
    pop.link_actions(a1, GOAL, g)

    return pop

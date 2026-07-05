from agents.epic_story_writer.clustering import cluster_programs

STRUCTURE_A = {
    "program_id": "PAYROLL01",
    "copybooks_referenced": ["EMPREC"],
    "call_graph": {"nodes": ["1000-MAIN"], "edges": []},
}

STRUCTURE_B = {
    "program_id": "TIMESHEET",
    "copybooks_referenced": ["EMPREC"],
    "call_graph": {"nodes": ["1000-MAIN"], "edges": []},
}

STRUCTURE_C = {
    "program_id": "REPORTGEN",
    "copybooks_referenced": [],
    "call_graph": {"nodes": [], "edges": []},
}


def test_shared_copybook_clusters_two_programs_together():
    clusters = cluster_programs([STRUCTURE_A, STRUCTURE_B])
    assert clusters == [["PAYROLL01", "TIMESHEET"]]


def test_no_shared_copybook_or_call_gives_one_program_per_cluster():
    clusters = cluster_programs([STRUCTURE_A, STRUCTURE_C])
    assert clusters == [["PAYROLL01"], ["REPORTGEN"]]


def test_call_graph_edge_clusters_two_programs_together():
    caller = {
        "program_id": "MAINDRV",
        "copybooks_referenced": [],
        "call_graph": {"nodes": ["1000-MAIN"], "edges": [{"from": "1000-MAIN", "to": "SUBCALC"}]},
    }
    callee = {
        "program_id": "SUBCALC",
        "copybooks_referenced": [],
        "call_graph": {"nodes": [], "edges": []},
    }
    clusters = cluster_programs([caller, callee])
    assert clusters == [["MAINDRV", "SUBCALC"]]


def test_single_program_with_no_structures_list_is_its_own_cluster():
    clusters = cluster_programs([STRUCTURE_C])
    assert clusters == [["REPORTGEN"]]


def test_empty_input_returns_no_clusters():
    assert cluster_programs([]) == []


def test_three_way_transitive_copybook_sharing_forms_one_cluster():
    third = {
        "program_id": "PAYSLIP",
        "copybooks_referenced": ["EMPREC"],
        "call_graph": {"nodes": [], "edges": []},
    }
    clusters = cluster_programs([STRUCTURE_A, STRUCTURE_B, third])
    assert clusters == [["PAYROLL01", "PAYSLIP", "TIMESHEET"]]


def test_output_order_is_deterministic_regardless_of_input_order():
    forward = cluster_programs([STRUCTURE_A, STRUCTURE_B, STRUCTURE_C])
    backward = cluster_programs([STRUCTURE_C, STRUCTURE_B, STRUCTURE_A])
    assert forward == backward

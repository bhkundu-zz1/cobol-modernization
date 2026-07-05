import pytest

from agents.mainframe_ingestion.adapter import ChangemanAdapter, EndevorAdapter, PanvaletAdapter, get_adapter


def test_get_adapter_mock_lists_and_pulls_fixture():
    adapter = get_adapter("mock")
    elements = adapter.list_elements(host="x", credential_ref="y", system="PAYSYS", subsystem="PAYROLL", element_type="COBOL")
    assert any(e["element_id"] == "PAYROLL01" for e in elements)

    source = adapter.get_source(
        host="x", credential_ref="y", system="PAYSYS", subsystem="PAYROLL", element_type="COBOL", element_id="PAYROLL01"
    )
    assert "PROGRAM-ID. PAYROLL01" in source

    metadata = adapter.get_metadata(
        host="x", credential_ref="y", system="PAYSYS", subsystem="PAYROLL", element_type="COBOL", element_id="PAYROLL01"
    )
    assert metadata["element_id"] == "PAYROLL01"
    assert metadata["tool"] == "mock"


@pytest.mark.parametrize("tool_name,adapter_cls", [("endevor", EndevorAdapter), ("panvalet", PanvaletAdapter), ("changeman", ChangemanAdapter)])
def test_real_adapters_raise_not_implemented(tool_name, adapter_cls):
    adapter = get_adapter(tool_name)
    assert isinstance(adapter, adapter_cls)
    with pytest.raises(NotImplementedError):
        adapter.list_elements(host="x", credential_ref="y", system="PAYSYS", subsystem="PAYROLL", element_type="COBOL")
    with pytest.raises(NotImplementedError):
        adapter.get_source(
            host="x", credential_ref="y", system="PAYSYS", subsystem="PAYROLL", element_type="COBOL", element_id="X"
        )


def test_unknown_tool_raises_value_error():
    with pytest.raises(ValueError):
        get_adapter("some-unsupported-tool")

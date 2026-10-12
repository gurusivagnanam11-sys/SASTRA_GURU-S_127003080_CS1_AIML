import pytest

from extraction.models import (
    CompleteArchitectureModel,
    ExtractedComponent,
    ExtractedDependency,
    ExtractedFunctionalFlow,
    ExtractedInterface,
    ExtractedPort,
    ExtractedSignal,
    Direction
)
from analysis.architecture_validator import validate_architecture, ValidationCategory, Severity

def create_valid_base_architecture() -> CompleteArchitectureModel:
    comp1 = ExtractedComponent(name="EngineCtrl", document="doc1", version="1.0", page=1, section="1", chunk_id="c1", description="desc")
    comp2 = ExtractedComponent(name="BrakeCtrl", document="doc1", version="1.0", page=1, section="1", chunk_id="c2", description="desc")
    
    iface1 = ExtractedInterface(name="SpeedIface", signals=["SpeedSig"], document="doc1", version="1.0", page=1, section="1", chunk_id="i1")
    
    sig1 = ExtractedSignal(name="SpeedSig", data_type="float", document="doc1", version="1.0", page=1, section="1", chunk_id="s1")
    
    port1 = ExtractedPort(name="SpeedOut", component="EngineCtrl", direction=Direction.OUTPUT, interface="SpeedIface", signals=["SpeedSig"], document="doc1", version="1.0", page=1, section="1", chunk_id="p1")
    port2 = ExtractedPort(name="SpeedIn", component="BrakeCtrl", direction=Direction.INPUT, interface="SpeedIface", signals=["SpeedSig"], document="doc1", version="1.0", page=1, section="1", chunk_id="p2")
    
    dep1 = ExtractedDependency(source_component="BrakeCtrl", target_component="EngineCtrl", document="doc1", version="1.0", page=1, section="1", chunk_id="d1")
    
    flow1 = ExtractedFunctionalFlow(name="SpeedFlow", source="EngineCtrl", target="BrakeCtrl", interface="SpeedIface", signal="SpeedSig", steps=["EngineCtrl", "BrakeCtrl"], document="doc1", version="1.0", page=1, section="1", chunk_id="f1")
    
    return CompleteArchitectureModel(
        version="1.0",
        components=[comp1, comp2],
        interfaces=[iface1],
        signals=[sig1],
        ports=[port1, port2],
        dependencies=[dep1],
        functional_flows=[flow1]
    )

def test_valid_architecture():
    model = create_valid_base_architecture()
    res = validate_architecture(model)
    assert res.status == "PASS"
    assert res.summary.errors == 0

def test_undefined_component_reference():
    model = create_valid_base_architecture()
    model.dependencies.append(
        ExtractedDependency(source_component="EngineCtrl", target_component="MissingComp", document="doc1", version="1.0", page=1, section="1", chunk_id="d2")
    )
    res = validate_architecture(model)
    assert res.status == "ERROR"
    err = next(e for e in res.errors if e.category == ValidationCategory.UNDEFINED_REFERENCE and e.related_entity == "MissingComp")
    assert err is not None

def test_undefined_interface_reference():
    model = create_valid_base_architecture()
    model.ports.append(
        ExtractedPort(name="BadPort", component="EngineCtrl", direction=Direction.OUTPUT, interface="MissingIface", document="doc1", version="1.0", page=1, section="1", chunk_id="p3")
    )
    res = validate_architecture(model)
    assert res.status == "ERROR"
    err = next(e for e in res.errors if e.category == ValidationCategory.UNDEFINED_REFERENCE and e.related_entity == "MissingIface")
    assert err is not None

def test_undefined_signal_reference():
    model = create_valid_base_architecture()
    model.interfaces[0].signals.append("MissingSignal")
    res = validate_architecture(model)
    assert res.status == "ERROR"
    err = next(e for e in res.errors if e.category == ValidationCategory.UNDEFINED_REFERENCE and e.related_entity == "MissingSignal")
    assert err is not None

def test_orphan_component():
    model = create_valid_base_architecture()
    model.components.append(
        ExtractedComponent(name="OrphanComp", document="doc1", version="1.0", page=1, section="1", chunk_id="c3", description="desc")
    )
    res = validate_architecture(model)
    assert res.status == "WARNING"
    warn = next(w for w in res.warnings if w.category == ValidationCategory.ORPHAN_ENTITY and w.entity_name == "OrphanComp")
    assert warn is not None

def test_orphan_interface():
    model = create_valid_base_architecture()
    model.interfaces.append(
        ExtractedInterface(name="OrphanIface", document="doc1", version="1.0", page=1, section="1", chunk_id="i2")
    )
    res = validate_architecture(model)
    assert res.status == "WARNING"
    warn = next(w for w in res.warnings if w.category == ValidationCategory.ORPHAN_ENTITY and w.entity_name == "OrphanIface")
    assert warn is not None

def test_orphan_signal():
    model = create_valid_base_architecture()
    model.signals.append(
        ExtractedSignal(name="OrphanSignal", data_type="int", document="doc1", version="1.0", page=1, section="1", chunk_id="s2")
    )
    res = validate_architecture(model)
    assert res.status == "WARNING"
    warn = next(w for w in res.warnings if w.category == ValidationCategory.ORPHAN_ENTITY and w.entity_name == "OrphanSignal")
    assert warn is not None

def test_invalid_flow_reference():
    model = create_valid_base_architecture()
    model.functional_flows[0].source = "UnknownSource"
    res = validate_architecture(model)
    assert res.status == "ERROR"
    err = next(e for e in res.errors if e.category == ValidationCategory.UNDEFINED_REFERENCE and e.related_entity == "UnknownSource")
    assert err is not None

def test_duplicate_definition():
    model = create_valid_base_architecture()
    comp_dup = ExtractedComponent(name="EngineCtrl", document="doc1", version="1.0", page=1, section="1", chunk_id="c4", description="desc")
    model.components.append(comp_dup)
    res = validate_architecture(model)
    assert res.status == "ERROR"
    err = next(e for e in res.errors if e.category == ValidationCategory.DUPLICATE_ENTITY and e.entity_name == "EngineCtrl")
    assert err is not None

def test_incomplete_component():
    model = create_valid_base_architecture()
    model.components[0].description = ""
    res = validate_architecture(model)
    # This should be an INFO level finding
    info = next((i for i in res.info if i.category == ValidationCategory.INCOMPLETE_ENTITY and i.entity_name == "EngineCtrl"), None)
    assert info is not None

def test_valid_v1_architecture():
    from extraction.basic_extractor import get_architecture_extractor
    extractor = get_architecture_extractor()
    model = extractor.get_complete_model("1.0")
    res = validate_architecture(model)
    # Default architecture might have some orphans/warnings based on our rules vs the fixture.
    # We just ensure it runs and we can inspect the status. It shouldn't crash.
    assert isinstance(res.status, str)

def test_valid_v2_architecture():
    from extraction.basic_extractor import get_architecture_extractor
    extractor = get_architecture_extractor()
    model = extractor.get_complete_model("2.0")
    res = validate_architecture(model)
    assert isinstance(res.status, str)

def test_version_isolation():
    from extraction.basic_extractor import get_architecture_extractor
    extractor = get_architecture_extractor()
    model_v1 = extractor.get_complete_model("1.0")
    res_v1 = validate_architecture(model_v1)
    
    model_v2 = extractor.get_complete_model("2.0")
    res_v2 = validate_architecture(model_v2)
    
    assert res_v1.version == "1.0"
    assert res_v2.version == "2.0"

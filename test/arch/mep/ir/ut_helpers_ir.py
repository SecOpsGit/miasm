# Toshiba MeP-c4 - unit tests helpers
# Guillaume Valadon <guillaume@valadon.net>

from miasm2.arch.mep.arch import mn_mep
from miasm2.arch.mep.sem import ir_mepb
from miasm2.arch.mep.regs import regs_init

from miasm2.ir.symbexec import SymbolicExecutionEngine
from miasm2.core.locationdb import LocationDB
from miasm2.core.utils import Disasm_Exception
from miasm2.ir.ir import AssignBlock
from miasm2.arch.mep.ira import ir_a_mepb
from miasm2.expression.expression import ExprId, ExprInt, ExprOp, ExprMem, ExprAssign, ExprLoc


def exec_instruction(mn_str, init_values, results, index=0, offset=0):
    """Symbolically execute an instruction and check the expected results."""

    # Assemble and disassemble the instruction
    instr = mn_mep.fromstring(mn_str, "b")
    instr.mode = "b"
    mn_bin = mn_mep.asm(instr)[index]
    try:
        instr = mn_mep.dis(mn_bin, "b")
    except Disasm_Exception:
        assert(False)  # miasm don't know what to do

    # Specify the instruction offset and compute the destination label
    instr.offset = offset
    loc_db = LocationDB()
    if instr.dstflow():
        instr.dstflow2label(loc_db)

    # Get the IR
    im = ir_mepb(loc_db)
    iir, eiir = im.get_ir(instr)

    # Filter out IRDst
    iir = [ir for ir in iir if not (isinstance(ir, ExprAssign) and
                                    isinstance(ir.dst, ExprId) and
                                    ir.dst.name == "IRDst")]

    # Prepare symbolic execution
    sb = SymbolicExecutionEngine(ir_a_mepb(loc_db), regs_init)

    # Assign int values before symbolic evaluation
    for expr_id, expr_value in init_values:
        sb.symbols[expr_id] = expr_value

    # Execute the IR
    ab = AssignBlock(iir)
    sb.eval_updt_assignblk(ab)

    # Check if expected expr_id were modified
    matched_results = 0
    for expr_id, expr_value in results:

        result = sb.eval_expr(expr_id)
        if isinstance(result, ExprLoc):
            addr = loc_db.get_location_offset(result.loc_key)
            if expr_value.arg == addr:
                matched_results += 1
                continue
        elif result == expr_value:
            matched_results += 1
            continue

    # Ensure that all expected results were verified
    if len(results) is not matched_results:
        print "Expected:", results
        print "Modified:", [r for r in sb.modified(mems=False)]
        assert(False)


def launch_tests(obj):
    """Call test methods by name"""

    test_methods = [name for name in dir(obj) if name.startswith("test")]

    for method in test_methods:
        print method
        try:
            getattr(obj, method)()
        except AttributeError as e:
            print "Method not found: %s" % method
            assert(False)
        print '-' * 42

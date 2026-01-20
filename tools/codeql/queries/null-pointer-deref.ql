/**
 * @name Null pointer dereference
 * @description Detects potential null pointer dereferences where a pointer may be null
 * @kind path-problem
 * @problem.severity error
 * @security-severity 7.5
 * @precision medium
 * @id cpp/null-pointer-dereference
 * @tags security
 *       reliability
 *       external/cwe/cwe-476
 */

import cpp
import semmle.code.cpp.dataflow.new.DataFlow

class AllocationFunction extends Function {
  AllocationFunction() {
    this.hasGlobalOrStdName(["malloc", "calloc", "realloc", "new", "new[]"])
  }
}

module NullPointerDerefConfig implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
    exists(FunctionCall fc |
      fc.getTarget() instanceof AllocationFunction and
      source.asExpr() = fc
    )
  }
  
  predicate isSink(DataFlow::Node sink) {
    exists(PointerDereferenceExpr deref |
      sink.asExpr() = deref.getOperand()
    ) or
    exists(ArrayExpr ae |
      sink.asExpr() = ae.getArrayBase()
    ) or
    exists(FunctionCall fc, int i |
      sink.asExpr() = fc.getArgument(i) and
      fc.getTarget().getParameter(i).getType() instanceof ReferenceType
    )
  }
  
  predicate isBarrier(DataFlow::Node node) {
    exists(IfStmt ifstmt, EqualityOperation eq |
      eq = ifstmt.getCondition().getAChild*() and
      (
        eq.getLeftOperand() = node.asExpr() or
        eq.getRightOperand() = node.asExpr()
      ) and
      ifstmt.getControlFlowNode().getASuccessor+() = node.asExpr().getControlFlowNode()
    )
  }
}

module NullPointerDerefFlow = DataFlow::Global<NullPointerDerefConfig>;

from NullPointerDerefFlow::PathNode source, NullPointerDerefFlow::PathNode sink
where
  NullPointerDerefFlow::flowPath(source, sink)
select sink.getNode(), source, sink, 
  "Potential null pointer dereference: pointer allocated at $@ may be null.", 
  source.getNode(), "allocation"

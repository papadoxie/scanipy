/**
 * @name Double-free vulnerability
 * @description Detects potential double-free vulnerabilities where the same memory is freed multiple times
 * @kind problem
 * @problem.severity error
 * @security-severity 9.0
 * @precision medium
 * @id cpp/double-free
 * @tags security
 *       external/cwe/cwe-415
 */

import cpp
import semmle.code.cpp.controlflow.Guards

class FreeCall extends FunctionCall {
  FreeCall() {
    this.getTarget().hasGlobalOrStdName(["free", "delete", "delete[]"])
  }
  
  Expr getFreedExpr() {
    result = this.getArgument(0)
  }
}

predicate sameFreeTarget(FreeCall fc1, FreeCall fc2) {
  exists(Variable v |
    fc1.getFreedExpr() = v.getAnAccess() and
    fc2.getFreedExpr() = v.getAnAccess() and
    fc1 != fc2
  )
}

predicate possiblyExecutedAfter(FreeCall fc1, FreeCall fc2) {
  fc2.getControlFlowNode().getASuccessor+() = fc1.getControlFlowNode()
  or
  exists(BasicBlock bb1, BasicBlock bb2 |
    bb1.contains(fc1.getControlFlowNode()) and
    bb2.contains(fc2.getControlFlowNode()) and
    bb1.getASuccessor+() = bb2
  )
}

from FreeCall fc1, FreeCall fc2, Variable v
where
  sameFreeTarget(fc1, fc2) and
  possiblyExecutedAfter(fc1, fc2) and
  fc1.getFreedExpr() = v.getAnAccess() and
  fc2.getFreedExpr() = v.getAnAccess() and
  // Exclude cases where the pointer is clearly reassigned between frees
  not exists(AssignExpr assign |
    assign.getLValue() = v.getAnAccess() and
    assign.getControlFlowNode().getASuccessor+() = fc1.getControlFlowNode() and
    fc2.getControlFlowNode().getASuccessor+() = assign.getControlFlowNode()
  )
select fc1, "Potential double-free: variable '" + v.getName() + "' may have been freed at $@", fc2, "this location"

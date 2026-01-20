/**
 * @name Memory corruption vulnerabilities
 * @description Finds potential memory corruption issues including buffer overflows,
 *              use-after-free, double-free, and null pointer dereferences in C/C++
 * @kind problem
 * @problem.severity error
 * @security-severity 9.0
 * @precision high
 * @id cpp/memory-corruption
 * @tags security
 *       external/cwe/cwe-119
 *       external/cwe/cwe-120
 *       external/cwe/cwe-416
 *       external/cwe/cwe-415
 */

import cpp
import semmle.code.cpp.dataflow.TaintTracking
import semmle.code.cpp.security.BufferWrite

from Expr source, Expr sink, string message
where
  (
    // Buffer overflow from strcpy/sprintf without bounds checking
    exists(FunctionCall fc |
      fc.getTarget().hasGlobalOrStdName(["strcpy", "strcat", "sprintf", "vsprintf", "gets"]) and
      sink = fc and
      message = "Unsafe function " + fc.getTarget().getName() + " may cause buffer overflow"
    )
    or
    // Use-after-free: accessing memory after free
    exists(Variable v, FunctionCall free, VariableAccess access |
      free.getTarget().hasGlobalOrStdName("free") and
      free.getArgument(0) = v.getAnAccess() and
      access = v.getAnAccess() and
      access.getControlFlowNode().postDominates(free.getControlFlowNode()) and
      sink = access and
      message = "Potential use-after-free of variable '" + v.getName() + "'"
    )
    or
    // Double-free: freeing the same pointer twice
    exists(Variable v, FunctionCall free1, FunctionCall free2 |
      free1.getTarget().hasGlobalOrStdName("free") and
      free2.getTarget().hasGlobalOrStdName("free") and
      free1 != free2 and
      free1.getArgument(0) = v.getAnAccess() and
      free2.getArgument(0) = v.getAnAccess() and
      free2.getControlFlowNode().postDominates(free1.getControlFlowNode()) and
      sink = free2 and
      message = "Potential double-free of variable '" + v.getName() + "'"
    )
    or
    // Null pointer dereference after allocation check
    exists(IfStmt ifstmt, EqualityOperation eq, PointerDereferenceExpr deref, Variable v |
      eq = ifstmt.getCondition().getAChild*() and
      eq.getAnOperand().getValue() = "0" and
      eq.getAnOperand() = v.getAnAccess() and
      deref.getOperand() = v.getAnAccess() and
      deref.getControlFlowNode().postDominates(ifstmt.getControlFlowNode()) and
      sink = deref and
      message = "Potential null pointer dereference of '" + v.getName() + "'"
    )
    or
    // Array indexing without bounds check
    exists(ArrayExpr ae, Variable array, VariableAccess index |
      ae.getArrayBase() = array.getAnAccess() and
      ae.getArrayOffset() = index and
      not exists(RelationalOperation ro |
        ro.getAnOperand() = index and
        ro.getAnOperand().getValue().toInt() <= array.getType().(ArrayType).getArraySize()
      ) and
      sink = ae and
      message = "Array access without bounds checking on '" + array.getName() + "'"
    )
  ) and
  source = sink
select sink, message

/**
 * @name Use-after-free vulnerability
 * @description Detects potential use-after-free vulnerabilities where memory is accessed after being freed
 * @kind path-problem
 * @problem.severity error
 * @security-severity 9.8
 * @precision medium
 * @id cpp/use-after-free
 * @tags security
 *       external/cwe/cwe-416
 */

import cpp
import semmle.code.cpp.dataflow.new.DataFlow

class FreeCall extends FunctionCall {
  FreeCall() {
    this.getTarget().hasGlobalOrStdName(["free", "delete", "delete[]"])
  }
  
  Expr getFreedExpr() {
    result = this.getArgument(0)
  }
}

module UseAfterFreeConfig implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
    exists(FreeCall fc |
      source.asExpr() = fc.getFreedExpr()
    )
  }
  
  predicate isSink(DataFlow::Node sink) {
    exists(PointerDereferenceExpr deref |
      sink.asExpr() = deref.getOperand()
    ) or
    exists(FunctionCall fc |
      sink.asExpr() = fc.getAnArgument() and
      not fc instanceof FreeCall
    ) or
    exists(ArrayExpr ae |
      sink.asExpr() = ae.getArrayBase()
    )
  }
}

module UseAfterFreeFlow = DataFlow::Global<UseAfterFreeConfig>;

from UseAfterFreeFlow::PathNode source, UseAfterFreeFlow::PathNode sink, FreeCall fc
where
  UseAfterFreeFlow::flowPath(source, sink) and
  fc.getFreedExpr() = source.getNode().asExpr()
select sink.getNode(), source, sink, "Potential use-after-free: memory freed at $@ is used here.", fc, "free call"

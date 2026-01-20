/**
 * @name Buffer overflow from unsafe string operations
 * @description Detects uses of unsafe string functions that can lead to buffer overflows
 * @kind problem
 * @problem.severity error
 * @security-severity 9.3
 * @precision high
 * @id cpp/buffer-overflow-unsafe-functions
 * @tags security
 *       external/cwe/cwe-120
 *       external/cwe/cwe-119
 *       external/cwe/cwe-787
 */

import cpp

from FunctionCall call, string unsafeFunc, string safeAlternative
where
  (
    call.getTarget().hasGlobalOrStdName("strcpy") and
    unsafeFunc = "strcpy" and
    safeAlternative = "strncpy or strlcpy"
    or
    call.getTarget().hasGlobalOrStdName("strcat") and
    unsafeFunc = "strcat" and
    safeAlternative = "strncat or strlcat"
    or
    call.getTarget().hasGlobalOrStdName("sprintf") and
    unsafeFunc = "sprintf" and
    safeAlternative = "snprintf"
    or
    call.getTarget().hasGlobalOrStdName("vsprintf") and
    unsafeFunc = "vsprintf" and
    safeAlternative = "vsnprintf"
    or
    call.getTarget().hasGlobalOrStdName("gets") and
    unsafeFunc = "gets" and
    safeAlternative = "fgets"
    or
    call.getTarget().hasGlobalOrStdName("scanf") and
    call.getArgument(0).getValue().regexpMatch(".*%s.*") and
    unsafeFunc = "scanf with %s" and
    safeAlternative = "scanf with width specifier (e.g., %99s)"
  )
select call, "Use of unsafe function '" + unsafeFunc + "' can lead to buffer overflow. Consider using " + safeAlternative + " instead."

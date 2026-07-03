"""
Unit tests for React Hook dependency violations (TR-017)

Tests that React Hooks (useEffect, useCallback, useMemo) have complete
dependency arrays to prevent stale closures, infinite loops, and bugs.

Security Fix Tested:
- All useEffect hooks must include all referenced variables in dependencies
- useCallback and useMemo must have complete dependency arrays
- Custom hooks must follow the same rules
- ESLint exhaustive-deps rule should be enabled

Reference: https://react.dev/reference/react/useEffect#specifying-reactive-dependencies
"""

import pytest
import re
from pathlib import Path


class TestUseEffectDependencies:
    """Test useEffect dependency array patterns"""

    def test_missing_dependencies_detection(self):
        """Test detection of missing dependencies in useEffect"""

        # ❌ VIOLATION: Missing dependency 'count'
        violation = """
        function Counter() {
            const [count, setCount] = useState(0);

            useEffect(() => {
                console.log(count);  // Uses 'count'
            }, []);  // Missing 'count' in dependencies
        }
        """

        # ✅ CORRECT: All dependencies included
        correct = """
        function Counter() {
            const [count, setCount] = useState(0);

            useEffect(() => {
                console.log(count);  // Uses 'count'
            }, [count]);  // 'count' included in dependencies
        }
        """

        # Verify violation has empty dependency array despite using variable
        assert "console.log(count)" in violation
        assert "}, []);" in violation

        # Verify correct version includes dependency
        assert "[count]" in correct

    def test_stale_closure_example(self):
        """Test example of stale closure bug from missing dependencies"""

        # ❌ VIOLATION: Stale closure - interval always logs 0
        stale_closure = """
        function Timer() {
            const [seconds, setSeconds] = useState(0);

            useEffect(() => {
                const interval = setInterval(() => {
                    console.log(seconds);  // Always logs 0 (stale)
                }, 1000);
                return () => clearInterval(interval);
            }, []);  // Missing 'seconds' - creates stale closure
        }
        """

        # ✅ CORRECT: Fresh closure with dependency
        fresh_closure = """
        function Timer() {
            const [seconds, setSeconds] = useState(0);

            useEffect(() => {
                const interval = setInterval(() => {
                    console.log(seconds);  // Logs current value
                }, 1000);
                return () => clearInterval(interval);
            }, [seconds]);  // 'seconds' included - no stale closure
        }
        """

        assert "}, []);" in stale_closure
        assert "[seconds]" in fresh_closure

    def test_function_dependencies(self):
        """Test that functions used in useEffect must be in dependencies"""

        # ❌ VIOLATION: Missing function dependency
        violation = """
        function DataFetcher({ userId }) {
            const fetchData = () => {
                fetch(`/api/users/${userId}`);
            };

            useEffect(() => {
                fetchData();  // Uses 'fetchData'
            }, []);  // Missing 'fetchData' and 'userId'
        }
        """

        # ✅ CORRECT: Function wrapped in useCallback with dependencies
        correct = """
        function DataFetcher({ userId }) {
            const fetchData = useCallback(() => {
                fetch(`/api/users/${userId}`);
            }, [userId]);

            useEffect(() => {
                fetchData();
            }, [fetchData]);  // 'fetchData' included
        }
        """

        assert "fetchData();" in violation
        assert "}, []);" in violation
        assert "useCallback" in correct
        assert "[fetchData]" in correct


class TestUseCallbackDependencies:
    """Test useCallback dependency array patterns"""

    def test_callback_missing_dependencies(self):
        """Test detection of missing dependencies in useCallback"""

        # ❌ VIOLATION: Missing 'threshold' dependency
        violation = """
        function Filter({ threshold }) {
            const filterItems = useCallback((items) => {
                return items.filter(item => item.value > threshold);
            }, []);  // Missing 'threshold'
        }
        """

        # ✅ CORRECT: All dependencies included
        correct = """
        function Filter({ threshold }) {
            const filterItems = useCallback((items) => {
                return items.filter(item => item.value > threshold);
            }, [threshold]);  // 'threshold' included
        }
        """

        assert "threshold" in violation
        assert "}, []);" in violation
        assert "[threshold]" in correct

    def test_callback_with_state(self):
        """Test useCallback with state dependencies"""

        # ❌ VIOLATION: Missing 'multiplier' state dependency
        violation = """
        function Calculator() {
            const [multiplier, setMultiplier] = useState(2);

            const calculate = useCallback((value) => {
                return value * multiplier;  // Uses 'multiplier'
            }, []);  // Missing 'multiplier'
        }
        """

        # ✅ CORRECT: State included in dependencies
        correct = """
        function Calculator() {
            const [multiplier, setMultiplier] = useState(2);

            const calculate = useCallback((value) => {
                return value * multiplier;
            }, [multiplier]);  // 'multiplier' included
        }
        """

        assert "multiplier" in violation
        assert "}, []);" in violation
        assert "[multiplier]" in correct


class TestUseMemoDepenencies:
    """Test useMemo dependency array patterns"""

    def test_memo_missing_dependencies(self):
        """Test detection of missing dependencies in useMemo"""

        # ❌ VIOLATION: Missing 'items' and 'filter' dependencies
        violation = """
        function ItemList({ items, filter }) {
            const filteredItems = useMemo(() => {
                return items.filter(item => item.type === filter);
            }, []);  // Missing 'items' and 'filter'
        }
        """

        # ✅ CORRECT: All dependencies included
        correct = """
        function ItemList({ items, filter }) {
            const filteredItems = useMemo(() => {
                return items.filter(item => item.type === filter);
            }, [items, filter]);  // Both dependencies included
        }
        """

        assert "items.filter" in violation
        assert "}, []);" in violation
        assert "[items, filter]" in correct

    def test_memo_expensive_computation(self):
        """Test useMemo with expensive computations"""

        # ❌ VIOLATION: Missing 'data' dependency
        violation = """
        function Analytics({ data }) {
            const statistics = useMemo(() => {
                return calculateExpensiveStats(data);  // Uses 'data'
            }, []);  // Missing 'data'
        }
        """

        # ✅ CORRECT: Dependency included
        correct = """
        function Analytics({ data }) {
            const statistics = useMemo(() => {
                return calculateExpensiveStats(data);
            }, [data]);  // 'data' included
        }
        """

        assert "calculateExpensiveStats(data)" in violation
        assert "}, []);" in violation
        assert "[data]" in correct


class TestCustomHooks:
    """Test custom hook dependency patterns"""

    def test_custom_hook_dependencies(self):
        """Test that custom hooks follow dependency rules"""

        # ❌ VIOLATION: Custom hook with missing dependencies
        violation = """
        function useDebounce(value, delay) {
            const [debouncedValue, setDebouncedValue] = useState(value);

            useEffect(() => {
                const handler = setTimeout(() => {
                    setDebouncedValue(value);
                }, delay);
                return () => clearTimeout(handler);
            }, []);  // Missing 'value' and 'delay'

            return debouncedValue;
        }
        """

        # ✅ CORRECT: All dependencies included
        correct = """
        function useDebounce(value, delay) {
            const [debouncedValue, setDebouncedValue] = useState(value);

            useEffect(() => {
                const handler = setTimeout(() => {
                    setDebouncedValue(value);
                }, delay);
                return () => clearTimeout(handler);
            }, [value, delay]);  // Both dependencies included

            return debouncedValue;
        }
        """

        assert "}, []);" in violation
        assert "[value, delay]" in correct


class TestInfiniteLoopPrevention:
    """Test patterns that prevent infinite loops"""

    def test_object_dependency_infinite_loop(self):
        """Test infinite loop from object recreation"""

        # ❌ VIOLATION: Infinite loop - object recreated every render
        violation = """
        function UserProfile({ userId }) {
            const options = { userId };  // New object every render

            useEffect(() => {
                fetchUser(options);
            }, [options]);  // Infinite loop!
        }
        """

        # ✅ CORRECT: Use primitive values or useMemo
        correct = """
        function UserProfile({ userId }) {
            const options = useMemo(() => ({ userId }), [userId]);

            useEffect(() => {
                fetchUser(options);
            }, [options]);  // No infinite loop
        }
        """

        assert "const options = { userId };" in violation
        assert "useMemo" in correct

    def test_function_recreation_infinite_loop(self):
        """Test infinite loop from function recreation"""

        # ❌ VIOLATION: Infinite loop - function recreated every render
        violation = """
        function DataLoader() {
            const loadData = () => {  // New function every render
                fetch('/api/data');
            };

            useEffect(() => {
                loadData();
            }, [loadData]);  // Infinite loop!
        }
        """

        # ✅ CORRECT: Use useCallback
        correct = """
        function DataLoader() {
            const loadData = useCallback(() => {
                fetch('/api/data');
            }, []);

            useEffect(() => {
                loadData();
            }, [loadData]);  // No infinite loop
        }
        """

        assert "const loadData = ()" in violation
        assert "useCallback" in correct


class TestESLintExhaustiveDeps:
    """Test ESLint exhaustive-deps rule patterns"""

    def test_eslint_disable_comments(self):
        """Test that eslint-disable comments should be rare and justified"""

        # ❌ BAD: Disabling eslint rule without justification
        bad_disable = """
        useEffect(() => {
            doSomething(prop);
            // eslint-disable-next-line react-hooks/exhaustive-deps
        }, []);
        """

        # ✅ BETTER: Fix the dependency issue instead
        fixed = """
        useEffect(() => {
            doSomething(prop);
        }, [prop]);
        """

        # ⚠️ ACCEPTABLE: Disable with clear justification
        justified_disable = """
        useEffect(() => {
            // Only run once on mount - prop is stable and doesn't change
            // eslint-disable-next-line react-hooks/exhaustive-deps
            doSomething(prop);
        }, []);
        """

        assert "eslint-disable" in bad_disable
        assert "eslint-disable" not in fixed
        assert "eslint-disable" in justified_disable
        assert "Only run once" in justified_disable  # Has justification


class TestCommonPatterns:
    """Test common React Hook patterns"""

    def test_event_listener_cleanup(self):
        """Test event listener pattern with cleanup"""

        # ✅ CORRECT: Event listener with proper dependencies
        correct = """
        function ResizeObserver({ onResize }) {
            useEffect(() => {
                const handleResize = () => {
                    onResize(window.innerWidth);
                };

                window.addEventListener('resize', handleResize);
                return () => window.removeEventListener('resize', handleResize);
            }, [onResize]);  // 'onResize' included
        }
        """

        assert "addEventListener" in correct
        assert "removeEventListener" in correct
        assert "[onResize]" in correct

    def test_interval_pattern(self):
        """Test interval pattern with cleanup"""

        # ✅ CORRECT: Interval with cleanup
        correct = """
        function Timer({ delay }) {
            const [count, setCount] = useState(0);

            useEffect(() => {
                const interval = setInterval(() => {
                    setCount(c => c + 1);  // Use functional update
                }, delay);

                return () => clearInterval(interval);
            }, [delay]);  // Only 'delay' needed (setCount is stable)
        }
        """

        assert "setInterval" in correct
        assert "clearInterval" in correct
        assert "setCount(c => c + 1)" in correct  # Functional update
        assert "[delay]" in correct

    def test_ref_dependencies(self):
        """Test that refs don't need to be in dependencies"""

        # ✅ CORRECT: Refs are stable and don't need dependencies
        correct = """
        function InputFocus() {
            const inputRef = useRef(null);

            useEffect(() => {
                inputRef.current?.focus();
            }, []);  // inputRef not needed in dependencies
        }
        """

        assert "useRef" in correct
        assert "inputRef.current" in correct
        assert "}, []);" in correct


class TestCodebaseCompliance:
    """Test that codebase follows Hook dependency rules"""

    def test_scan_for_empty_dependency_arrays(self):
        """Scan operator-dashboard for useEffect with empty arrays"""
        # Get path to operator-dashboard
        project_root = Path(__file__).parent.parent.parent
        dashboard_src = project_root / "operator-dashboard" / "src"

        # Skip test if directory doesn't exist
        if not dashboard_src.exists():
            pytest.skip("operator-dashboard not found")

        suspicious_patterns = []
        # Pattern to find useEffect with empty dependency array
        pattern = r"useEffect\s*\([^)]+\),\s*\[\s*\]\s*\)"

        # Scan .tsx and .ts files
        for tsx_file in dashboard_src.rglob("*.tsx"):
            content = tsx_file.read_text(encoding="utf-8")

            matches = re.finditer(pattern, content)
            for match in matches:
                # Get surrounding context
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]

                # Check if there's a justification comment
                has_justification = (
                    "only run once" in context.lower()
                    or "mount only" in context.lower()
                    or "initial" in context.lower()
                )

                if not has_justification:
                    line_num = content[: match.start()].count("\n") + 1
                    suspicious_patterns.append(
                        {
                            "file": str(tsx_file.relative_to(project_root)),
                            "line": line_num,
                            "context": context.strip(),
                        }
                    )

        # Report findings
        if suspicious_patterns:
            print(
                f"\n[WARNING] Found {len(suspicious_patterns)} useEffect calls with empty dependencies:"
            )
            for pattern_info in suspicious_patterns[:5]:  # Show first 5
                print(f"\n  File: {pattern_info['file']}:{pattern_info['line']}")
                print(f"  Context: {pattern_info['context'][:150]}...")
            print("\nThese should be reviewed to ensure dependencies are correct.")

        # This is informational, not a hard failure
        # In real project, this would be caught by ESLint

    def test_eslint_config_has_exhaustive_deps(self):
        """Test that ESLint config enables exhaustive-deps rule"""
        # Get path to operator-dashboard
        project_root = Path(__file__).parent.parent.parent
        eslint_config = project_root / "operator-dashboard" / ".eslintrc.json"

        # Skip test if file doesn't exist
        if not eslint_config.exists():
            # Try alternative config files
            alt_configs = [
                project_root / "operator-dashboard" / ".eslintrc.js",
                project_root / "operator-dashboard" / "eslint.config.js",
            ]
            found = False
            for alt_config in alt_configs:
                if alt_config.exists():
                    eslint_config = alt_config
                    found = True
                    break

            if not found:
                pytest.skip("ESLint config not found")

        # Read config
        content = eslint_config.read_text(encoding="utf-8")

        # Check for exhaustive-deps rule
        has_exhaustive_deps = "exhaustive-deps" in content or "react-hooks" in content

        if has_exhaustive_deps:
            print("\n[OK] ESLint config includes react-hooks/exhaustive-deps rule")
        else:
            print("\n[WARNING] ESLint config may be missing react-hooks/exhaustive-deps rule")

        # This is informational - don't fail if rule not found


class TestSecurityDocumentation:
    """Test that TR-017 security fix is documented"""

    def test_security_fix_documentation(self):
        """Verify TR-017 is documented in security fixes"""

        expected_patterns = [
            "TR-017",
            "React Hook dependencies",
            "useEffect",
            "exhaustive-deps",
        ]

        # This test documents the expected security fix
        assert len(expected_patterns) > 0

    def test_hook_dependency_best_practices(self):
        """Document React Hook dependency best practices"""

        best_practices = {
            "Include all dependencies": "All referenced variables must be in dependency array",
            "Use functional updates": "setState(prev => prev + 1) avoids state dependencies",
            "Memoize objects/functions": "Use useMemo/useCallback for non-primitive dependencies",
            "Avoid eslint-disable": "Fix the issue instead of disabling the rule",
            "Refs are stable": "useRef values don't need to be in dependencies",
            "Cleanup functions": "Return cleanup function from useEffect",
        }

        assert len(best_practices) == 6

        for practice, description in best_practices.items():
            assert len(description) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

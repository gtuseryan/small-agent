"""代码分析相关工具"""

import os
import re
from .base import BaseTool, ToolResult


class AnalyzeCodeTool(BaseTool):
    """分析代码文件的逻辑结构、潜在问题和优化建议"""

    @property
    def name(self) -> str:
        return "analyze_code"

    @property
    def description(self) -> str:
        return (
            "分析指定代码文件的逻辑结构、函数/类定义、依赖关系、"
            "潜在Bug和安全漏洞。支持 Python、Java、Go、JavaScript、TypeScript。"
            "返回结构化的代码分析报告。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要分析的代码文件路径（绝对路径或相对于当前目录的路径）",
                },
                "focus": {
                    "type": "string",
                    "enum": ["structure", "bugs", "security", "performance", "all"],
                    "description": "分析焦点：structure(结构)、bugs(缺陷)、security(安全)、performance(性能)、all(全部)",
                },
            },
            "required": ["file_path"],
        }

    def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get("file_path", "")
        focus = kwargs.get("focus", "all")

        validation = self._validate_params(kwargs, ["file_path"])
        if validation:
            return ToolResult.fail(validation)

        if not os.path.isfile(file_path):
            return ToolResult.fail(f"文件不存在: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
        except Exception as e:
            return ToolResult.fail(f"读取文件失败: {str(e)}")

        ext = os.path.splitext(file_path)[1]
        lines = code.split("\n")

        report_parts = [f"## 代码分析报告: {file_path}\n"]
        report_parts.append(f"文件类型: {ext}  |  总行数: {len(lines)}  |  字符数: {len(code)}\n")

        # 结构分析
        if focus in ("structure", "all"):
            report_parts.append("### 代码结构")
            funcs = self._find_functions(code, ext)
            classes = self._find_classes(code, ext)
            imports = self._find_imports(code, ext)

            report_parts.append(f"- 导入模块: {len(imports)} 个")
            if imports[:10]:
                for imp in imports[:10]:
                    report_parts.append(f"  - `{imp}`")
            report_parts.append(f"- 类定义: {len(classes)} 个")
            for cls in classes:
                report_parts.append(f"  - `{cls}`")
            report_parts.append(f"- 函数/方法定义: {len(funcs)} 个")
            for fn in funcs:
                report_parts.append(f"  - `{fn}`")

        # Bug检测
        if focus in ("bugs", "all"):
            report_parts.append("\n### 潜在问题")
            issues = self._detect_issues(code, ext)
            if issues:
                for issue in issues:
                    report_parts.append(f"- {issue}")
            else:
                report_parts.append("- 未发现明显的代码问题（基础静态检查）")

        # 安全检测
        if focus in ("security", "all"):
            report_parts.append("\n### 安全检查")
            sec_issues = self._security_check(code, ext)
            if sec_issues:
                for s in sec_issues:
                    report_parts.append(f"- {s}")
            else:
                report_parts.append("- 基础安全检查未发现明显问题")

        # 性能检测
        if focus in ("performance", "all"):
            report_parts.append("\n### 性能提示")
            perf_hints = self._performance_check(code, ext)
            if perf_hints:
                for p in perf_hints:
                    report_parts.append(f"- {p}")
            else:
                report_parts.append("- 未发现明显的性能问题")

        return ToolResult.ok(
            "\n".join(report_parts),
            lines=len(lines),
            functions=len(funcs),
            classes=len(classes),
        )

    def _find_functions(self, code: str, ext: str) -> list:
        patterns = {
            ".py": r"^\s*def\s+(\w+)",
            ".java": r"^\s*(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(",
            ".go": r"^\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(",
            ".js": r"^\s*(?:async\s+)?function\s+(\w+)|^\s*(?:async\s+)?(\w+)\s*=\s*(?:async\s+)?\(.*\)\s*=>",
            ".ts": r"^\s*(?:async\s+)?function\s+(\w+)|^\s*(?:async\s+)?(\w+)\s*[:=]\s*(?:async\s+)?\(.*\)\s*=>",
        }
        pattern = patterns.get(ext, r"^\s*(?:def|func|function)\s+(\w+)")
        return list(set(re.findall(pattern, code, re.MULTILINE)))

    def _find_classes(self, code: str, ext: str) -> list:
        patterns = {
            ".py": r"^\s*class\s+(\w+)",
            ".java": r"^\s*(?:public\s+)?class\s+(\w+)",
            ".ts": r"^\s*(?:export\s+)?class\s+(\w+)",
            ".js": r"^\s*class\s+(\w+)",
        }
        pattern = patterns.get(ext, r"class\s+(\w+)")
        return re.findall(pattern, code, re.MULTILINE)

    def _find_imports(self, code: str, ext: str) -> list:
        patterns = {
            ".py": r"^(?:import\s+(\S+)|from\s+(\S+)\s+import)",
            ".java": r"^import\s+([\w.]+)",
            ".go": r"^import\s+\"([^\"]+)\"",
            ".js": r"^(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))",
            ".ts": r"^(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))",
        }
        pattern = patterns.get(ext, r"(?:import|require)\s+[\(]?['\"]?(\S+)['\"]?")
        matches = re.findall(pattern, code, re.MULTILINE)
        return [m[0] or m[1] for m in matches if m[0] or m[1]][:20]

    def _detect_issues(self, code: str, ext: str) -> list:
        issues = []
        # 通用问题模式
        checks = [
            (r"print\s*\(.*\)", "包含 print() 调试语句，建议使用 logging 模块"),
            (r"except\s*:", "存在裸 except 语句，建议指定具体异常类型"),
            (r"pass\s*$", "存在空的 pass 语句块，可能为未完成的功能"),
            (r"TODO|FIXME|HACK", "存在 TODO/FIXME 标记，可能为未完成的工作"),
            (r"\.\.\.\s*$", "存在省略号占位符，可能为未实现的功能"),
        ]
        for pattern, msg in checks:
            if re.search(pattern, code, re.MULTILINE):
                issues.append(f"⚠️ {msg}")
        return issues

    def _security_check(self, code: str, ext: str) -> list:
        issues = []
        checks = [
            (r"password\s*=\s*['\"][^'\"]+['\"]", "硬编码密码/密钥"),
            (r"os\.system\s*\(|subprocess\.call\s*\(|exec\s*\(|eval\s*\(", "存在命令执行/代码注入风险"),
            (r"SELECT\s+.*\s+WHERE\s+.*%s|execute\s*\(.*%\s*\w+", "SQL 查询可能存在注入风险（使用参数化查询）"),
            (r"\.innerHTML\s*=", "使用 innerHTML 可能存在 XSS 风险"),
        ]
        for pattern, msg in checks:
            if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
                issues.append(f"🔴 {msg}")
        return issues

    def _performance_check(self, code: str, ext: str) -> list:
        hints = []
        if re.search(r"\.append\(.*\)", code):
            if re.search(r"for\s+.+in\s+.+:", code):
                hints.append("💡 循环中包含 append 操作，考虑使用列表推导式优化（Python）")
        if re.search(r"\+\s*=\s*['\"]", code) and re.search(r"for\s+.+in", code):
            hints.append("💡 循环中使用字符串拼接，建议使用 join() 方法")
        return hints


class ReviewDiffTool(BaseTool):
    """审查代码 Diff，识别 Bug、安全漏洞和规范问题"""

    @property
    def name(self) -> str:
        return "review_diff"

    @property
    def description(self) -> str:
        return (
            "审查代码变更（git diff 输出），逐行分析新增和修改的代码，"
            "识别潜在的逻辑错误、安全漏洞、代码规范违规和测试覆盖缺失。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "diff_content": {
                    "type": "string",
                    "description": "git diff 输出的完整内容",
                },
                "context": {
                    "type": "string",
                    "description": "变更的背景说明（可选，如：修复登录Bug、新增支付接口）",
                },
            },
            "required": ["diff_content"],
        }

    def execute(self, **kwargs) -> ToolResult:
        diff = kwargs.get("diff_content", "")
        context = kwargs.get("context", "")
        validation = self._validate_params(kwargs, ["diff_content"])
        if validation:
            return ToolResult.fail(validation)

        report = ["## 代码变更审查报告\n"]
        if context:
            report.append(f"变更背景: {context}\n")

        lines = diff.split("\n")
        added_lines = [l for l in lines if l.startswith("+") and not l.startswith("+++")]
        removed_lines = [l for l in lines if l.startswith("-") and not l.startswith("---")]
        files_changed = [l for l in lines if l.startswith("diff --git")]

        report.append(f"- 变更文件: {len(files_changed)} 个")
        report.append(f"- 新增行: {len(added_lines)} 行")
        report.append(f"- 删除行: {len(removed_lines)} 行\n")

        report.append("### 审查要点")

        checks = []
        for line in added_lines:
            content = line[1:].strip()
            if not content:
                continue
            if re.search(r"print\s*\(", content):
                checks.append(f"⚠️ 调试代码: `{content[:80]}`")
            if re.search(r"(?i)password|secret|token|api_key", content) and re.search(r"['\"]\w{8,}['\"]", content):
                checks.append(f"🔴 可能的硬编码凭证: `{content[:80]}`")
            if re.search(r"except\s*:", content):
                checks.append(f"⚠️ 裸 except: `{content[:80]}`")

        if checks:
            for c in checks[:20]:
                report.append(f"- {c}")
        else:
            report.append("- 初步审查未发现明显问题")

        report.append("\n### 审查建议")
        report.append("- 请确认所有新增的外部输入都经过验证和转义")
        report.append("- 请确认关键的变更逻辑有对应的单元测试覆盖")
        report.append("- 请检查变更是否引入了新的外部依赖")

        return ToolResult.ok(
            "\n".join(report),
            files_count=len(files_changed),
            added_count=len(added_lines),
            removed_count=len(removed_lines),
        )


class GenerateDocTool(BaseTool):
    """根据代码自动生成 API 文档或 README"""

    @property
    def name(self) -> str:
        return "generate_doc"

    @property
    def description(self) -> str:
        return (
            "读取代码文件或目录，自动生成 API 文档、README 或模块说明文档。"
            "支持从代码注释和函数签名中提取信息。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "目标代码文件或目录路径",
                },
                "doc_type": {
                    "type": "string",
                    "enum": ["api", "readme", "module"],
                    "description": "文档类型：api(API文档)、readme(项目README)、module(模块说明)",
                },
            },
            "required": ["target"],
        }

    def execute(self, **kwargs) -> ToolResult:
        target = kwargs.get("target", "")
        doc_type = kwargs.get("doc_type", "api")
        validation = self._validate_params(kwargs, ["target"])
        if validation:
            return ToolResult.fail(validation)

        if os.path.isfile(target):
            files = [target]
        elif os.path.isdir(target):
            files = [
                os.path.join(root, f)
                for root, _, filenames in os.walk(target)
                for f in filenames if not f.startswith(".") and not f.startswith("__")
            ][:20]
        else:
            return ToolResult.fail(f"目标路径不存在: {target}")

        doc = [f"## {'API 文档' if doc_type == 'api' else '模块说明' if doc_type == 'module' else '项目概述'}\n"]
        doc.append(f"生成目标: {target}\n")

        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            rel_path = os.path.relpath(fpath, target) if os.path.isdir(target) else os.path.basename(fpath)
            doc.append(f"### {rel_path}\n")

            # 提取文档字符串和注释
            comments = re.findall(r'^\s*"""(.*?)"""', content, re.DOTALL)
            if comments:
                doc.append(comments[0].strip()[:300] + "\n")

            # 提取函数签名
            funcs = re.findall(r"^\s*def\s+(\w+)\s*\((.*?)\)", content, re.MULTILINE)
            if funcs:
                doc.append("**函数/方法:**\n")
                for name, params in funcs[:10]:
                    doc.append(f"- `{name}({params})`\n")

            # 提取类
            classes = re.findall(r"^\s*class\s+(\w+)(?:\((.*?)\))?:", content, re.MULTILINE)
            if classes:
                doc.append("**类:**\n")
                for cls, parent in classes:
                    parent_str = f" 继承自 `{parent}`" if parent else ""
                    doc.append(f"- `{cls}`{parent_str}\n")

            doc.append("")

        return ToolResult.ok("\n".join(doc), files_count=len(files))

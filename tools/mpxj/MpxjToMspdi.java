// Minimal MPXJ converter used by importers/mpp_mpxj.py (invoked as a subprocess).
//
// Reads any MPXJ-supported schedule file (.mpp / .mpx / .xer / MSPDI XML / ...)
// via the universal reader and writes it back out as MS Project MSPDI XML, which
// the pure-Python importer (parse_msp_xml) then reads. This keeps the JVM fully
// OUT of the Python process (Commandment 1: never in-process JPype).
//
// Because MSPDI XML does not carry the source file's saved VIEWS (the named task
// filters and groups a planner built — feature #10), every successful conversion
// ALSO writes a sidecar JSON at "<output>.views.json" with the full filter
// criteria trees (recursive AND/OR, literal / field-to-field / prompt / null
// operands) and group clauses, which importers/msp_views.py parses onto the
// Schedule model. A file with no saved views gets an empty sidecar.
//
// Three modes:
//   ONE-SHOT   MpxjToMspdi <input> <output>     — convert a single file and exit.
//   BATCH      MpxjToMspdi --server             — a persistent, heap-capped JVM that
//              converts many files in ONE process (v4 Feature 2 scale). Reads
//              "<input>\t<output>" lines from stdin, writes one tagged status line per
//              request to stdout ("@@SF@@ OK" / "@@SF@@ ERR <msg>"), and loops until EOF
//              or a "__QUIT__" line. One unreadable file is reported, never fatal — the
//              same JVM keeps serving the rest of a large folder ingest. This is the
//              difference between one JVM boot and thousands for a folder of .mpp files.
//   EVAL       MpxjToMspdi --eval <input> <output.json>  — the filter PARITY oracle:
//              evaluates every prompt-free task filter with MPXJ's own
//              Filter.evaluate() over every task and dumps {"<filter>": [uid, ...]}.
//              The Python evaluator (engine/msp_filters.py) is gate-tested against
//              this output on the real reference .mpp, so "faithful reproduction"
//              is proven against the reference implementation, not assumed.
//
// Build + wire-up: tools/mpxj/setup.sh (or setup.ps1). Verified against MPXJ 16.2.0
// (package org.mpxj; the Maven groupId is still net.sf.mpxj).
//
//   javac -cp 'lib/*' --release 17 -d classes MpxjToMspdi.java
//   export SF_MPXJ_CMD="java -cp classes:lib/* MpxjToMspdi {input} {output}"
//
// Exit codes (one-shot / eval): 0 ok; 1 bad args; 2 MPXJ did not recognize the input.

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

import org.mpxj.FieldType;
import org.mpxj.Filter;
import org.mpxj.GenericCriteria;
import org.mpxj.GenericCriteriaPrompt;
import org.mpxj.Group;
import org.mpxj.GroupClause;
import org.mpxj.ProjectFile;
import org.mpxj.Task;
import org.mpxj.mspdi.MSPDIWriter;
import org.mpxj.reader.UniversalProjectReader;

public class MpxjToMspdi {
    // A unique prefix on every status line so the Python side can ignore any stray
    // JVM/MPXJ logging that lands on stdout and never mis-read it as a status.
    private static final String TAG = "@@SF@@ ";

    public static void main(String[] args) throws Exception {
        if (args.length == 1 && "--server".equals(args[0])) {
            runServer();
            return;
        }
        if (args.length == 3 && "--eval".equals(args[0])) {
            ProjectFile project = new UniversalProjectReader().read(args[1]);
            if (project == null) {
                System.err.println("MPXJ could not recognize the file: " + args[1]);
                System.exit(2);
            }
            writeUtf8(args[2], evalJson(project));
            return;
        }
        if (args.length < 2) {
            System.err.println(
                "usage: MpxjToMspdi <input> <output>  |  --server  |  --eval <input> <out.json>");
            System.exit(1);
        }
        ProjectFile project = new UniversalProjectReader().read(args[0]);
        if (project == null) {
            System.err.println("MPXJ could not recognize the file: " + args[0]);
            System.exit(2);
        }
        convert(project, args[1]);
    }

    // The full per-file conversion: the MSPDI XML plus the saved-views sidecar.
    private static void convert(ProjectFile project, String output) throws Exception {
        new MSPDIWriter().write(project, output);
        writeUtf8(output + ".views.json", viewsJson(project));
    }

    // Batch/server loop: one heap-capped JVM converts many files across a single ingest.
    private static void runServer() throws Exception {
        BufferedReader in =
            new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        out.println(TAG + "READY");
        String line;
        while ((line = in.readLine()) != null) {
            if ("__QUIT__".equals(line)) {
                break;
            }
            int tab = line.indexOf('\t');
            if (tab < 0) {
                out.println(TAG + "ERR malformed request");
                continue;
            }
            String input = line.substring(0, tab);
            String output = line.substring(tab + 1);
            try {
                ProjectFile project = new UniversalProjectReader().read(input);
                if (project == null) {
                    out.println(TAG + "ERR MPXJ could not recognize the file");
                    continue;
                }
                convert(project, output);
                out.println(TAG + "OK");
            } catch (Throwable t) {
                // isolate: one bad file must never kill the server mid-ingest
                out.println(TAG + "ERR " + oneLine(t));
            }
        }
    }

    private static String oneLine(Throwable t) {
        String msg = t.getClass().getSimpleName();
        if (t.getMessage() != null) {
            msg += ": " + t.getMessage().replace('\n', ' ').replace('\r', ' ');
        }
        return msg;
    }

    private static void writeUtf8(String path, String text) throws Exception {
        Files.write(Paths.get(path), text.getBytes(StandardCharsets.UTF_8));
    }

    // --- saved-views sidecar -------------------------------------------------------------------

    private static String viewsJson(ProjectFile project) {
        StringBuilder sb = new StringBuilder("{\"filters\":[");
        boolean first = true;
        // The MPP reader can register the built-in filters in BOTH the task and the resource
        // list; dedupe on (type, name) so each saved filter appears exactly once.
        java.util.Set<String> seen = new java.util.HashSet<>();
        for (List<Filter> filters : List.of(
                project.getFilters().getTaskFilters(),
                project.getFilters().getResourceFilters())) {
            for (Filter f : filters) {
                if (!seen.add((f.isTaskFilter() ? "T:" : "R:") + f.getName())) {
                    continue;
                }
                if (!first) {
                    sb.append(',');
                }
                first = false;
                filterJson(sb, f);
            }
        }
        sb.append("],\"groups\":[");
        first = true;
        for (Group g : project.getGroups()) {
            if (!first) {
                sb.append(',');
            }
            first = false;
            groupJson(sb, g);
        }
        return sb.append("]}").toString();
    }

    private static void filterJson(StringBuilder sb, Filter f) {
        List<GenericCriteriaPrompt> prompts = f.getPrompts();
        sb.append("{\"name\":").append(q(f.getName()))
          .append(",\"isTaskFilter\":").append(f.isTaskFilter())
          .append(",\"showRelatedSummaryRows\":").append(f.getShowRelatedSummaryRows())
          .append(",\"promptCount\":").append(prompts == null ? 0 : prompts.size())
          .append(",\"criteria\":");
        if (f.getCriteria() == null) {
            sb.append("null");
        } else {
            criteriaJson(sb, f.getCriteria());
        }
        sb.append('}');
    }

    private static void criteriaJson(StringBuilder sb, GenericCriteria c) {
        String op = c.getOperator().name();
        sb.append("{\"op\":").append(q(op));
        if ("AND".equals(op) || "OR".equals(op)) {
            sb.append(",\"children\":[");
            List<GenericCriteria> kids = c.getCriteriaList();
            for (int i = 0; i < kids.size(); i++) {
                if (i > 0) {
                    sb.append(',');
                }
                criteriaJson(sb, kids.get(i));
            }
            sb.append(']');
        } else {
            FieldType field = c.getLeftValue();
            if (field != null) {
                sb.append(",\"field\":").append(q(field.getName()))
                  .append(",\"fieldEnum\":").append(q(field.name()));
            }
            // IS_ANY_VALUE takes no operand, IS_(NOT_)WITHIN two, every other leaf one; a Java
            // null operand is a REAL value (the "EQUALS <null>" absent-value test), kept as such.
            int count = "IS_ANY_VALUE".equals(op) ? 0
                : ("IS_WITHIN".equals(op) || "IS_NOT_WITHIN".equals(op)) ? 2 : 1;
            sb.append(",\"operands\":[");
            for (int i = 0; i < count; i++) {
                if (i > 0) {
                    sb.append(',');
                }
                operandJson(sb, c.getValue(i));
            }
            sb.append(']');
        }
        sb.append('}');
    }

    private static void operandJson(StringBuilder sb, Object value) {
        if (value == null) {
            sb.append("{\"kind\":\"null\"}");
        } else if (value instanceof GenericCriteriaPrompt) {
            sb.append("{\"kind\":\"prompt\",\"text\":")
              .append(q(((GenericCriteriaPrompt) value).getPrompt())).append('}');
        } else if (value instanceof FieldType) {
            FieldType ft = (FieldType) value;
            sb.append("{\"kind\":\"field\",\"text\":").append(q(ft.getName()))
              .append(",\"fieldEnum\":").append(q(ft.name())).append('}');
        } else {
            sb.append("{\"kind\":\"literal\",\"text\":").append(q(String.valueOf(value)))
              .append(",\"valueType\":").append(q(value.getClass().getSimpleName())).append('}');
        }
    }

    private static void groupJson(StringBuilder sb, Group g) {
        sb.append("{\"name\":").append(q(g.getName()))
          .append(",\"showSummaryTasks\":").append(g.getShowSummaryTasks())
          .append(",\"clauses\":[");
        List<GroupClause> clauses = g.getGroupClauses();
        for (int i = 0; i < clauses.size(); i++) {
            if (i > 0) {
                sb.append(',');
            }
            GroupClause clause = clauses.get(i);
            FieldType field = clause.getField();
            sb.append("{\"field\":").append(field == null ? "null" : q(field.getName()))
              .append(",\"fieldEnum\":").append(field == null ? "null" : q(field.name()))
              .append(",\"ascending\":").append(clause.getAscending())
              .append(",\"groupOn\":").append(clause.getGroupOn())
              .append(",\"interval\":").append(strOrNull(clause.getGroupInterval()))
              .append(",\"startAt\":").append(strOrNull(clause.getStartAt()))
              .append('}');
        }
        sb.append("]}");
    }

    private static String strOrNull(Object value) {
        return value == null ? "null" : q(String.valueOf(value));
    }

    // --- filter parity oracle (--eval) ---------------------------------------------------------

    private static String evalJson(ProjectFile project) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Filter f : project.getFilters().getTaskFilters()) {
            if (!f.isTaskFilter()) {
                continue; // "All Resources" parked in the task list — not evaluable over tasks
            }
            List<GenericCriteriaPrompt> prompts = f.getPrompts();
            if (prompts != null && !prompts.isEmpty()) {
                continue; // interactive filters need answers; their parity is pinned in unit tests
            }
            if (!first) {
                sb.append(',');
            }
            first = false;
            sb.append(q(f.getName())).append(":[");
            boolean firstUid = true;
            for (Task t : project.getTasks()) {
                if (t.getUniqueID() == null || !f.evaluate(t, null)) {
                    continue;
                }
                if (!firstUid) {
                    sb.append(',');
                }
                firstUid = false;
                sb.append(t.getUniqueID());
            }
            sb.append(']');
        }
        return sb.append('}').toString();
    }

    // --- minimal JSON string quoting (no external dependency) -----------------------------------

    private static String q(String s) {
        if (s == null) {
            return "null";
        }
        StringBuilder sb = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
                }
            }
        }
        return sb.append('"').toString();
    }
}

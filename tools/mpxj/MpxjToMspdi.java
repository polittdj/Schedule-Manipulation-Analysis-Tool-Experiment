// Minimal MPXJ converter used by importers/mpp_mpxj.py (invoked as a subprocess).
//
// Reads any MPXJ-supported schedule file (.mpp / .mpx / .xer / MSPDI XML / ...)
// via the universal reader and writes it back out as MS Project MSPDI XML, which
// the pure-Python importer (parse_msp_xml) then reads. This keeps the JVM fully
// OUT of the Python process (Commandment 1: never in-process JPype).
//
// Two modes:
//   ONE-SHOT   MpxjToMspdi <input> <output>     — convert a single file and exit.
//   BATCH      MpxjToMspdi --server             — a persistent, heap-capped JVM that
//              converts many files in ONE process (v4 Feature 2 scale). Reads
//              "<input>\t<output>" lines from stdin, writes one tagged status line per
//              request to stdout ("@@SF@@ OK" / "@@SF@@ ERR <msg>"), and loops until EOF
//              or a "__QUIT__" line. One unreadable file is reported, never fatal — the
//              same JVM keeps serving the rest of a large folder ingest. This is the
//              difference between one JVM boot and thousands for a folder of .mpp files.
//
// Build + wire-up: see docs/MPXJ.md. Verified against MPXJ 16.2.0 (package
// org.mpxj; the Maven groupId is still net.sf.mpxj).
//
//   javac -cp 'lib/*' --release 17 -d classes MpxjToMspdi.java
//   export SF_MPXJ_CMD="java -cp classes:lib/* MpxjToMspdi {input} {output}"
//
// Exit codes (one-shot): 0 ok; 1 bad args; 2 MPXJ did not recognize the input format.

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

import org.mpxj.ProjectFile;
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
        if (args.length < 2) {
            System.err.println("usage: MpxjToMspdi <input> <output>  |  MpxjToMspdi --server");
            System.exit(1);
        }
        ProjectFile project = new UniversalProjectReader().read(args[0]);
        if (project == null) {
            System.err.println("MPXJ could not recognize the file: " + args[0]);
            System.exit(2);
        }
        new MSPDIWriter().write(project, args[1]);
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
                new MSPDIWriter().write(project, output);
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
}

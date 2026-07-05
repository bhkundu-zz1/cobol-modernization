       IDENTIFICATION DIVISION.
       PROGRAM-ID. TIMESHEET.
       AUTHOR. COBOL-MODERNIZATION-HARNESS.
      *----------------------------------------------------------------
      * Second sample fixture program, deliberately sharing the PAYRATES
      * copybook with PAYROLL01.CBL so the epic-story-writer agent's
      * clustering logic (agents/epic_story_writer/clustering.py) has a
      * real multi-program case to group into one epic, exercising the
      * "shared copybook" edge (not a call_graph edge).
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT TIMESHEET-FILE ASSIGN TO TIMEMSTR
               ORGANIZATION IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  TIMESHEET-FILE.
       01  TIMESHEET-RECORD.
           COPY PAYRATES.

       WORKING-STORAGE SECTION.
       01  WS-EMPLOYEE-ID          PIC 9(6).
       01  WS-DAYS-WORKED          PIC 9(2).
       01  WS-END-OF-FILE          PIC X(01) VALUE 'N'.

       PROCEDURE DIVISION.
       1000-MAIN.
           OPEN INPUT TIMESHEET-FILE
           PERFORM UNTIL WS-END-OF-FILE = 'Y'
               READ TIMESHEET-FILE
                   AT END MOVE 'Y' TO WS-END-OF-FILE
                   NOT AT END PERFORM 2000-VALIDATE-DAYS
               END-READ
           END-PERFORM
           CLOSE TIMESHEET-FILE
           STOP RUN.

       2000-VALIDATE-DAYS.
           IF WS-DAYS-WORKED > 7
               DISPLAY 'INVALID DAYS WORKED FOR EMPLOYEE ' WS-EMPLOYEE-ID
           END-IF.

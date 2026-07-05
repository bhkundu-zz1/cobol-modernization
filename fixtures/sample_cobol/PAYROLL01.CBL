       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL01.
       AUTHOR. COBOL-MODERNIZATION-HARNESS.
      *----------------------------------------------------------------
      * Sample fixture program used to verify the ingestion, structural
      * analysis, and recommendation pipeline end-to-end. Deliberately
      * small and self-contained: one main paragraph, one calculation
      * paragraph, one unresolved external CALL to a rate-lookup
      * routine, one copybook reference.
      *----------------------------------------------------------------
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT EMPLOYEE-FILE ASSIGN TO EMPMASTR
               ORGANIZATION IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  EMPLOYEE-FILE.
       01  EMPLOYEE-RECORD.
           COPY PAYRATES.

       WORKING-STORAGE SECTION.
       01  WS-EMPLOYEE-ID          PIC 9(6).
       01  WS-HOURS-WORKED         PIC 9(3)V99.
       01  WS-HOURLY-RATE          PIC 9(3)V99.
       01  WS-GROSS-PAY            PIC 9(6)V99 VALUE ZERO.
       01  WS-OVERTIME-HOURS       PIC 9(3)V99 VALUE ZERO.
       01  WS-OVERTIME-RATE        PIC 9(3)V99.
       01  WS-RATE-LOOKUP-STATUS   PIC X(01).
       01  WS-END-OF-FILE          PIC X(01) VALUE 'N'.

       PROCEDURE DIVISION.
       1000-MAIN.
           OPEN INPUT EMPLOYEE-FILE
           PERFORM UNTIL WS-END-OF-FILE = 'Y'
               READ EMPLOYEE-FILE
                   AT END MOVE 'Y' TO WS-END-OF-FILE
                   NOT AT END PERFORM 2000-CALC-GROSS
               END-READ
           END-PERFORM
           CLOSE EMPLOYEE-FILE
           STOP RUN.

       2000-CALC-GROSS.
      *    Look up the current hourly rate for this employee from the
      *    external rate table maintained by another subsystem. This
      *    program does not own that data — SUBRTN99 is not defined in
      *    this source or its copybook, so this call is an unresolved
      *    external reference for structural-analysis purposes.
           CALL 'SUBRTN99' USING WS-EMPLOYEE-ID
                                  WS-HOURLY-RATE
                                  WS-RATE-LOOKUP-STATUS

           IF WS-HOURS-WORKED > 40
               COMPUTE WS-OVERTIME-HOURS = WS-HOURS-WORKED - 40
               COMPUTE WS-OVERTIME-RATE = WS-HOURLY-RATE * 1.5
               COMPUTE WS-GROSS-PAY =
                   (40 * WS-HOURLY-RATE) +
                   (WS-OVERTIME-HOURS * WS-OVERTIME-RATE)
           ELSE
               COMPUTE WS-GROSS-PAY = WS-HOURS-WORKED * WS-HOURLY-RATE
           END-IF.

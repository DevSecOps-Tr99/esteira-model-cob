//POC001   JOB (POC),'ESTEIRA MODEL COB',
//             CLASS=A,
//             MSGCLASS=X,
//             NOTIFY=&SYSUID
//*
//* Cenario 1 - sucesso: cria um dataset dentro do padrao de
//* nomenclatura ESTM.<APP>.<ENV>.<RESOURCE>. Esperado: RC 0000,
//* Quality Gate 100/100, Security Gate PASSED.
//*
//STEP01   EXEC PGM=IEFBR14
//*
//DD01     DD DSN=ESTM.POC.TU.TESTDATA,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(TRK,(1,1)),
//            UNIT=SYSDA

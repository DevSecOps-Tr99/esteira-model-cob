//POC002   JOB (POC),'ESTEIRA MODEL COB',
//             CLASS=A,
//             MSGCLASS=X,
//             NOTIFY=&SYSUID
//*
//* Cenario 2 - warning: dataset fora do padrao de nomenclatura
//* esperado (ESTM.<APP>.<ENV>.<RESOURCE>). Esperado: Quality Gate
//* WARNING, pipeline segue ou exige aprovacao manual.
//*
//STEP01   EXEC PGM=IEFBR14
//*
//DD01     DD DSN=POC.TEST.DATA,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(TRK,(1,1)),
//            UNIT=SYSDA

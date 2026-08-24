//POC003   JOB (POC),'ESTEIRA MODEL COB',
//             CLASS=A,
//             MSGCLASS=X,
//             NOTIFY=&SYSUID
//*
//* Cenario 3 - bloqueado: tentativa de exclusao de dataset em
//* qualifier de producao. Esperado: Security Gate FAILED, regra
//* critica PROD_DATASET_DELETE, deploy bloqueado antes do adapter.
//*
//STEP01   EXEC PGM=IDCAMS
//SYSPRINT DD  SYSOUT=*
//SYSIN    DD  *
  DELETE PROD.CLIENTES
/*

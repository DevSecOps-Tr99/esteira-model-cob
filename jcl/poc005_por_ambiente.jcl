//POC005   JOB (POC),'ESTEIRA MODEL COB',
//             CLASS=A,
//             MSGCLASS=X,
//             NOTIFY=&SYSUID
//*
//* Cenario 5 - parametros por ambiente: mesmo job, mesmo dataset e
//* mesma logica de SORT em TU/TI/PRD - so o SPACE alocado muda
//* (producao aloca mais espaco), espelhando um padrao real encontrado
//* em JCLs cedidos pelo banco (jcl/real/, nao versionado). O
//* placeholder na linha do SPACE e substituido por
//* esteira_model_cob/templating.py a partir de
//* config/jcl_env_params.yml antes da validacao - ver
//* docs/reuniao-endevor-jcl-binarios.md. Isso substitui o padrao real
//* observado (3 copias inteiras do arquivo, uma por ambiente, mantidas
//* a mao) por uma unica fonte versionada + valores explicitos por
//* ambiente.
//*
//STEP01   EXEC PGM=SORT
//SORTIN   DD DSN=ESTM.POC.TU.SORTIN,DISP=SHR
//SORTOUT  DD DSN=ESTM.POC.TU.SORTOUT,
//            DISP=(NEW,CATLG,DELETE),
//            UNIT=SYSDA,
//            SPACE=(TRK,(${SPACE_PRIMARY},${SPACE_SECONDARY}),RLSE)
//SYSIN    DD *
  SORT FIELDS=COPY
/*

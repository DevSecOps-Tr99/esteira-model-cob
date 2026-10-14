//ESTMX001 JOB '${ACCT}','${PROGRAMMER}',CLASS=${CLASS},
//             MSGCLASS=${MSGCLASS},SCHENV=${SCHENV},NOTIFY=${NOTIFY}
//JOBLIB   DD DSN=${HLQ}.LOADLIB,DISP=SHR
//*
//STEP01   EXEC PGM=SORT
//*
//* ***    PROJETO:ESTEIRA MODEL COB - PUBLICACAO POR AMBIENTE
//* ***    SISTEMA:ESTM
//* ***    FREQUENCIA:A PEDIDO
//* ***    CONVERTE ARQUIVO DE CLIENTES PARA O LAYOUT NOVO
//*
//* Modelo unico versionado. Cada placeholder vem das GitHub variables
//* do Environment (JCL_<NOME>) ou, rodando local, de
//* config/jcl_env_params.yml. A esteira grava um arquivo por ambiente
//* (ESTMX001TU.jcl, ESTMX001TI.jcl, ESTMX001PRD.jcl), no mesmo padrao
//* das copias por ambiente dos JCLs reais - ver
//* docs/ambiente-poc-azure.md.
//*
//SORTIN   DD DSN=${HLQ}.CLIENTES(0),
//       DISP=SHR
//SORTOUT  DD DSN=${HLQ}.CLIENTES(+1),
//       DISP=(,CATLG,DELETE),
//       UNIT=${UNIT},
//       SPACE=(TRK,(${SPACE_PRIMARY},${SPACE_SECONDARY}),RLSE),
//       DCB=(LRECL=0290,RECFM=FB),
//       DATACLAS=${DATACLAS}
//SYSOUT   DD SYSOUT=*
//SYSIN    DD *
  SORT FIELDS=(1,10,CH,A)
  OUTREC BUILD=(1,80,C'*',81,209)
  END
/*

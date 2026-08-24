package com.esteiramodelcob.proleap;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import io.proleap.cobol.asg.metamodel.CompilationUnit;
import io.proleap.cobol.asg.metamodel.Program;
import io.proleap.cobol.asg.metamodel.ProgramUnit;
import io.proleap.cobol.asg.metamodel.data.DataDivision;
import io.proleap.cobol.asg.runner.impl.CobolParserRunnerImpl;
import io.proleap.cobol.preprocessor.CobolPreprocessor.CobolSourceFormatEnum;

/**
 * Wrapper minimo em torno do ProLeap COBOL Parser para a esteira-model-cob.
 *
 * Escopo intencionalmente reduzido para a Fase 1 (POC): prova que a esteira
 * consegue gerar um AST/ASG real a partir de um fonte COBOL e resolver a
 * DATA DIVISION do programa. Regras semanticas em cima do AST (variavel nao
 * inicializada, SQL embutido sem bind, etc.) ficam para a Fase 2, apos um
 * levantamento mais detalhado da API de travessia do ProLeap
 * (io.proleap.cobol.asg.metamodel.procedure.* e data.datadescription.*),
 * que nao foi confirmada em detalhe nesta primeira entrega - ver
 * docs/seguranca.md.
 */
public final class AstDump {

    private static final Pattern PROGRAM_ID_PATTERN =
        Pattern.compile("PROGRAM-ID\\.\\s+([A-Za-z0-9-]+)", Pattern.CASE_INSENSITIVE);

    private AstDump() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Uso: AstDump <arquivo.cbl>");
            System.exit(2);
        }

        File cobolFile = new File(args[0]);
        String source = new String(Files.readAllBytes(Paths.get(cobolFile.getPath())));
        String programId = extractProgramId(source);

        boolean parsedOk = false;
        boolean hasDataDivision = false;
        boolean hasWorkingStorage = false;
        String error = null;

        try {
            Program program = new CobolParserRunnerImpl()
                .analyzeFile(cobolFile, CobolSourceFormatEnum.FIXED);
            CompilationUnit compilationUnit = program.getCompilationUnit(programId);
            ProgramUnit programUnit = compilationUnit.getProgramUnit();
            DataDivision dataDivision = programUnit.getDataDivision();

            parsedOk = true;
            hasDataDivision = dataDivision != null;
            hasWorkingStorage = hasDataDivision && dataDivision.getWorkingStorageSection() != null;
        } catch (Exception ex) {
            error = ex.getClass().getSimpleName() + ": " + ex.getMessage();
        }

        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append("\"sourceFile\":\"").append(escape(cobolFile.getPath())).append("\",");
        json.append("\"programId\":\"").append(escape(programId)).append("\",");
        json.append("\"parsedOk\":").append(parsedOk).append(",");
        json.append("\"hasDataDivision\":").append(hasDataDivision).append(",");
        json.append("\"hasWorkingStorage\":").append(hasWorkingStorage);
        if (error != null) {
            json.append(",\"error\":\"").append(escape(error)).append("\"");
        }
        json.append("}");

        System.out.println(json);
    }

    private static String extractProgramId(String source) {
        Matcher matcher = PROGRAM_ID_PATTERN.matcher(source);
        return matcher.find() ? matcher.group(1) : "UNKNOWN";
    }

    private static String escape(String value) {
        return value == null ? "" : value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}

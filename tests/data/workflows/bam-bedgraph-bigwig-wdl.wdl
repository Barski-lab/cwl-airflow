version 1.0


workflow pipeline {
    input {
        File bam_file                       # Input BAM file, sorted by coordinates
        File chrom_length_file              # Tab delimited chromosome length file: <chromName><\t><chromSize>
    }
    call bam_to_bedgraph {
        input:
            bam_file = bam_file
    }
    call sort_bedgraph {
        input:
            bedgraph_file = bam_to_bedgraph.bedgraph_file
    }
    call sorted_bedgraph_to_bigwig {
        input:
            sorted_bedgraph_file = sort_bedgraph.sorted_bedgraph_file,
            chrom_length_file = chrom_length_file
    }
    output {
        File bigwig_file = sorted_bedgraph_to_bigwig.bigwig_file
    }
}


task bam_to_bedgraph {
    input {
        File bam_file
    }
    output {
        File bedgraph_file = stdout()
    }
    command {
        bedtools genomecov -bg -ibam ${bam_file}
    }    
    runtime {
        docker: "biowardrobe2/bedtools2:v2.26.0"
    }
}


task sort_bedgraph {
    input {
        File bedgraph_file
    }
    output {
        File sorted_bedgraph_file = stdout()
    }
    command {
        sort -k 1,1 -k 2,2n ${bedgraph_file}
    }    
    runtime {
        docker: "biowardrobe2/scidap:v0.0.2"
    }
}


task sorted_bedgraph_to_bigwig {
    input {
        File sorted_bedgraph_file
        File chrom_length_file
    }
    command {
        bedGraphToBigWig ${sorted_bedgraph_file} ${chrom_length_file} genome_coverage.bigWig
    }
    output {
        File bigwig_file = "genome_coverage.bigWig"
    }
    runtime {
        docker: "biowardrobe2/ucscuserapps:v358"
    }
}
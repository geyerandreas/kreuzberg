# Docling Technical Report

Version 1.0

Christoph Auer Maksym Lysak Ahmed Nassar Michele Dolfi Nikolaos Livathinos Panos Vagenas Cesar Berrospi Ramis Matteo Omenetti Fabian Lindlbauer Kasper Dinkla Lokesh Mishra Yusik Kim Shubham Gupta Rafael Teixeira de Lima Valery Weber Lucas Morin Ingmar Meijer Viktor Kuropiatnyk Peter W. J. Staar

AI4K Group, IBM Research Ruschlikon, Switzerland

## Abstract

This technical report introduces Docling, an easy to use, self-contained, MIT-licensed open-source package for PDF document conversion. It is powered by state-of-the-art specialized AI models for layout analysis (DocLayNet) and table structure recognition (TableFormer), and runs efficiently on commodity hardware in a small resource budget. The code interface allows for easy extensibility and addition of new features and models.

## 1 Introduction

Converting PDF documents back into a machine-processable format has been a major challenge for decades due to their huge variability in formats, weak standardization and printing-optimized characteristic, which discards most structural features and metadata. With the advent of LLMs and popular application patterns such as retrieval-augmented generation (RAG), leveraging the rich content embedded in PDFs has become ever more relevant. In the past decade, several powerful document understanding solutions have emerged on the market, most of which are commercial software, cloud offerings and most recently, multi-modal vision-language models. As of today, only a handful of open-source tools cover PDF conversion, leaving a significant feature and quality gap to proprietary solutions.

With Docling, we open-source a very capable and efficient document conversion tool which builds on the powerful, specialized AI models and datasets for layout analysis and table structure recognition we developed and presented in the recent past. Docling is designed as a simple, self-contained python library with permissive license, running entirely locally on commodity hardware. Its code architecture allows for easy extensibility and addition of new features and models.

Here is what Docling delivers today:

- Converts PDF documents to JSON or Markdown format, stable and lightning fast
- Understands detailed page layout, reading order, locates figures and recovers table structures
- Extracts metadata from the document, such as title, authors, references and language
- Optionally applies OCR, e.g. for scanned PDFs
- Can be configured to be optimal for batch-mode (i.e high throughput, low time-to-solution) or interactive mode (compromise on efficiency, low time-to-solution)
- Can leverage different accelerators (GPU, MPS, etc).

## 2 Getting Started

To use Docling, you can simply install the docling package from PyPI. Documentation and examples are available in our GitHub repository at github.com/DS4SD/docling. All required model assets are downloaded to a local huggingface datasets cache on first use, unless you choose to pre-install the model assets in advance.

Docling provides an easy code interface to convert PDF documents from file system, URLs or binary streams, and retrieve the output in either JSON or Markdown format. For convenience, separate methods are offered to convert single documents or batches of documents. A basic usage example is illustrated below. Further examples are available in the Docling code repository.

```
from docling.document_converter import DocumentConverter
source = "https://arxiv.org/pdf/2206.01062"  # PDF path or URL
converter = DocumentConverter()
result = converter.convert_single(source)
print(result.render_as_markdown())  # output: "## DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis [...]"
```

Optionally, you can configure custom pipeline features and runtime options, such as turning on or off features (e.g. OCR, table structure recognition), enforcing limits on the input document size, and defining the budget of CPU threads. Advanced usage examples and options are documented in the README file. Docling also provides a Dockerfile to demonstrate how to install and run it inside a container.

## 3 Processing pipeline

Docling implements a linear pipeline of operations, which execute sequentially on each given document (see Fig. 1). Each document is first parsed by a PDF backend, which retrieves the programmatic text tokens, consisting of string content and its coordinates on the page, and also renders a bitmap image of each page to support downstream operations. Then, the standard model pipeline applies a sequence of AI models independently on every page in the document to extract features and content, such as layout and table structures. Finally, the results from all pages are aggregated and passed through a post-processing stage, which augments metadata, detects the document language, infers reading-order and eventually assembles a typed document object which can be serialized to JSON or Markdown.

### 3.1 PDF backends

Two basic requirements to process PDF documents in our pipeline are a) to retrieve all text content and their geometric coordinates on each page and b) to render the visual representation of each page as it would appear in a PDF viewer. Both these requirements are encapsulated in Docling's PDF backend interface. While there are several open-source PDF parsing libraries available for python, we faced major obstacles with all of them for different reasons, among which were restrictive licensing (e.g. pymupdf), poor speed or unrecoverable quality issues, such as merged text cells across far-apart text tokens or table columns (pypdfium, PyPDF).

We therefore decided to provide multiple backend choices, and additionally open-source a custom-built PDF parser, which is based on the low-level qpdf library. It is made available in a separate package named docling-parse and powers the default PDF backend in Docling. As an alternative, we provide a PDF backend relying on pypdfium, which may be a safe backup choice in certain cases, e.g. if issues are seen with particular font encodings.

### 3.2 AI models

As part of Docling, we initially release two highly capable AI models to the open-source community, which have been developed and published recently by our team. The first model is a layout analysis model, an accurate object-detector for page elements. The second model is TableFormer, a state-of-the-art table structure recognition model. We provide the pre-trained weights (hosted on huggingface) and a separate package for the inference code as docling-ibm-models. Both models are also powering the open-access deepsearch-experience, our cloud-native service for knowledge exploration tasks.

**Layout Analysis Model**

Our layout analysis model is an object-detector which predicts the bounding-boxes and classes of various elements on the image of a given page. Its architecture is derived from RT-DETR and re-trained on DocLayNet, our popular human-annotated dataset for document-layout analysis, among other proprietary datasets. For inference, our implementation relies on the onnxruntime.

The Docling pipeline feeds page images at 72 dpi resolution, which can be processed on a single CPU with sub-second latency. All predicted bounding-box proposals for document elements are post-processed to remove overlapping proposals based on confidence and size, and then intersected with the text tokens in the PDF to group them into meaningful and complete units such as paragraphs, section titles, list items, captions, figures or tables.

**Table Structure Recognition**

The TableFormer model, first published in 2022 and since refined with a custom structure token language, is a vision-transformer model for table structure recovery. It can predict the logical row and column structure of a given table based on an input image, and determine which table cells belong to column headers, row headers or the table body. Compared to earlier approaches, TableFormer handles many characteristics of tables, such as partial or no borderlines, empty cells, rows or columns, cell spans and hierarchy both on column-heading or row-heading level, tables with inconsistent indentation or alignment and other complexities. For inference, our implementation relies on PyTorch.

The Docling pipeline feeds all table objects detected in the layout analysis to the TableFormer model, by providing an image-crop of the table and the included text cells. TableFormer structure predictions are matched back to the PDF cells in post-processing to avoid expensive re-transcription text in the table image. Typical tables require between 2 and 6 seconds to be processed on a standard CPU, strongly depending on the amount of included table cells.

**OCR**

Docling provides optional support for OCR, for example to cover scanned PDFs or content in bitmaps images embedded on a page. In our initial release, we rely on EasyOCR, a popular third-party OCR library with support for many languages. Docling, by default, feeds a high-resolution page image (216 dpi) to the OCR engine, to allow capturing small print detail in decent quality. While EasyOCR delivers reasonable transcription quality, we observe that it runs fairly slow on CPU (upwards of 30 seconds per page).

We are actively seeking collaboration from the open-source community to extend Docling with additional OCR backends and speed improvements.

### 3.3 Assembly

In the final pipeline stage, Docling assembles all prediction results produced on each page into a well-defined datatype that encapsulates a converted document, as defined in the auxiliary package docling-core. The generated document object is passed through a post-processing model which leverages several algorithms to augment features, such as detection of the document language, correcting the reading order, matching figures with captions and labelling metadata such as title, authors and references. The final output can then be serialized to JSON or transformed into a Markdown representation at the users request.

### 3.4 Extensibility

Docling provides a straight-forward interface to extend its capabilities, namely the model pipeline. A model pipeline constitutes the central part in the processing, following initial document parsing and preceding output assembly, and can be fully customized by sub-classing from an abstract base-class (BaseModelPipeline) or cloning the default model pipeline. This effectively allows to fully customize the chain of models, add or replace models, and introduce additional pipeline configuration parameters. To use a custom model pipeline, the custom pipeline class to instantiate can be provided as an argument to the main document conversion methods. We invite everyone in the community to propose additional or alternative models and improvements.

Implementations of model classes must satisfy the python Callable interface. The __call__ method must accept an iterator over page objects, and produce another iterator over the page objects which were augmented with the additional features predicted by the model, by extending the provided PagePredictions data model accordingly.

## 4 Performance

In this section, we establish some reference numbers for the processing speed of Docling and the resource budget it requires. All tests in this section are run with default options on our standard test set distributed with Docling, which consists of three papers from arXiv and two IBM Redbooks, with a total of 225 pages. Measurements were taken using both available PDF backends on two different hardware systems: one MacBook Pro M3 Max, and one bare-metal server running Ubuntu 20.04 LTS on an Intel Xeon E5-2690 CPU. For reproducibility, we fixed the thread budget (through setting OMP NUM THREADS environment variable) once to 4 (Docling default) and once to 16 (equal to full core count on the test hardware). All results are shown in Table 1.

If you need to run Docling in very low-resource environments, please consider configuring the pypdfium backend. While it is faster and more memory efficient than the default docling-parse backend, it will come at the expense of worse quality results, especially in table structure recovery. Establishing GPU acceleration support for the AI models is currently work-in-progress and largely untested, but may work implicitly when CUDA is available and discovered by the onnxruntime and torch runtimes backing the Docling pipeline. We will deliver updates on this topic at in a future version of this report.

| CPU | Thread budget | native backend TTS | native backend Pages/s | native backend Mem | pypdfium backend TTS | pypdfium backend Pages/s | pypdfium backend Mem |
|---|---|---|---|---|---|---|---|
| Apple M3 Max (16 cores) | 4 | 177 s | 1.27 | 6.20 GB | 103 s | 2.18 | 2.56 GB |
| Apple M3 Max (16 cores) | 16 | 167 s | 1.34 | | 92 s | 2.45 | |
| Intel Xeon E5-2690 (16 cores) | 4 | 375 s | 0.60 | 6.16 GB | 239 s | 0.94 | 2.42 GB |
| Intel Xeon E5-2690 (16 cores) | 16 | 244 s | 0.92 | | 143 s | 1.57 | |

## 5 Applications

Thanks to the high-quality, richly structured document conversion achieved by Docling, its output qualifies for numerous downstream applications. For example, Docling can provide a base for detailed enterprise document search, passage retrieval or classification use-cases, or support knowledge extraction pipelines, allowing specific treatment of different structures in the document, such as tables, figures, section structure or references. For popular generative AI application patterns, such as retrieval-augmented generation (RAG), we provide quackling, an open-source package which capitalizes on Docling's feature-rich document output to enable document-native optimized vector embedding and chunking. It plugs in seamlessly with LLM frameworks such as LlamaIndex. Since Docling is fast, stable and cheap to run, it also makes for an excellent choice to build large-scale document processing pipelines, e.g. to fuel model training datasets.

## 6 Future work and contributions

We are planning to extend Docling with several new features in our future roadmap. Among the planned features are a figure-classifier model, which will allow to identify the type of a figure (chart, plot, schematic, photo, etc.) and further improve downstream processing. Additionally, we plan to introduce an equation recognition model to improve the handling of equations and formulas for STEM documents. A high-priority task is the support of more document formats beyond PDF, for which we are aiming to integrate parsers for common formats such as MS Word (docx), Powerpoint (pptx) and HTML.

We warmly welcome open-source contributions from the community to extend and improve Docling. In particular, we are looking for contributions on alternative OCR models, additional document format parsers, and models that can improve the understanding and enrichment of documents.

## References

- [1] EasyOCR. https://github.com/JaidedAI/EasyOCR, 2024.
- [2] PyTorch. https://pytorch.org, 2024.
- [3] Amazon Textract, Google Document AI, Azure Document Intelligence, 2024.
- [4] QPDF. https://github.com/qpdf/qpdf, 2024.
- [5] ONNX Runtime. https://onnxruntime.ai, 2024.
- [6] Poppler. https://poppler.freedesktop.org/, 2024.
- [7] PyMuPDF. https://github.com/pymupdf/PyMuPDF, 2024.
- [8] Jerry Liu. LlamaIndex, 11 2022.
- [9] Maksym Lysak, Ahmed Nassar, Nikolaos Livathinos, Christoph Auer, and Peter Staar. Optimized table tokenization for table structure recognition. In Document Analysis and Recognition - ICDAR 2023, 2023.
- [10] Thomas Pfitzner, David Eppstein, and Elad Verbin. Poppler utils, 2024.
- [11] Birgit Pfitzmann, Christoph Auer, Michele Dolfi, Ahmed S. Nassar, and Peter Staar. DocLayNet: A large human-annotated dataset for document-layout segmentation. In Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining, 2022.
- [12] Ahmed Nassar, Nikolaos Livathinos, Maksym Lysak, and Peter Staar. TableFormer: Table structure understanding with transformers. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2022.
- [13] Birgit Pfitzmann, Christoph Auer, Michele Dolfi, Ahmed S. Nassar, and Peter Staar. DocLayNet: A large human-annotated dataset for document-layout segmentation. In Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining, 2022.
- [14] PyPDF. https://github.com/py-pdf/pypdf, 2024.
- [15] PyPDFium2. https://github.com/nicegui-dev/pypdfium2, 2024.
- [16] Yian Zhao, Wenyu Lv, Shangliang Xu, Jinman Wei, Guanzhong Wang, Qingqing Dang, Yi Liu, and Jie Chen. DETRs beat YOLOs on real-time object detection. In Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), 2024.

## Appendix

In this section, we illustrate a few examples of Docling's output in Markdown and JSON.

DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis

Birgit Pfitzmann Christoph Auer Michele Dolfi

Ahmed S. Nassar Peter Staar

2 2 0 2 ABSTRACT n u J ] V .C s c [ v 2 6 0 rms PP) - Te ication (T res Publ 1 .0 6 Procedu erminal Guide - T rt Users' FAA Cha 2 : v i X r a CCS CONCEPTS

KEYWORDS

DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis ABSTRACT CCS CONCEPTS KEYWORDS ACM Reference Format:

1 INTRODUCTION

Figure 2: Title page of the DocLayNet paper (arxiv.org/pdf/2206.01062) - left PDF, right rendered Markdown. If recognized, metadata such as authors are appearing first under the title. Text content inside figures is currently dropped, the caption is retained and linked to the figure in the JSON representation (not shown).

Baselines for Object Detection

5 EXPERIMENTS

Figure 3: Page 6 of the DocLayNet paper. If recognized, metadata such as authors are appearing first under the title. Elements recognized as page headers or footers are suppressed in Markdown to deliver uninterrupted content in reading order. Tables are inserted in reading order. The paragraph in "5. Experiments" wrapping over the column end is broken up in two and interrupted by the table.

KDD '22, August 14–18, 2022, Washington, DC, USA Birgit Pfitzmann, Christoph Auer, Michele Dolfi, Ahmed S. Nassar, and Peter Staar Table 1: DocLayNet dataset overview. Along with the frequency of each class label, we present the relative occurrence (as % of row "Total") in the train, test and validation sets. The inter-annotator agreement is computed as the mAP@0.5-0.95 metric between pairwise annotations from the triple-annotated pages, from which we obtain accuracy ranges.

A B

% of Total triple inter-annotator mAP @ 0.5-0.95 (%) class label Count Train Test Val All Fin Man Sci Law Pat Ten Caption 22524 2.04 1.77 2.32 84-89 40-61 86-92 94-99 95-99 69-78 n/a Footnote 6318 0.60 0.31 0.58 83-91 n/a 100 62-88 85-94 n/a 82-97 Formula 25027 2.25 1.90 2.96 83-85 n/a n/a 84-87 86-96 n/a n/a List-item 185660 17.19 13.34 15.82 87-88 74-83 90-92 97-97 81-85 75-88 93-95 Page-footer 70878 6.51 5.58 6.00 93-94 88-90 95-96 100 92-97 100 96-98 Page-header 58022 5.10 6.70 5.06 85-89 66-76 90-94 98-100 91-92 97-99 81-86 Picture 45976 4.21 2.78 5.31 69-71 56-59 82-86 69-82 80-95 66-71 59-76 Section-header 142884 12.60 15.77 12.85 83-84 76-81 90-92 94-95 87-94 69-73 78-86 Table 34733 3.20 2.27 3.60 77-81 75-80 83-86 98-99 58-80 79-84 70-85 Text 510377 45.82 49.28 45.00 84-86 81-86 88-93 89-93 87-92 71-79 87-95 Title 5071 0.47 0.30 0.50 60-72 24-63 50-63 94-100 82-96 68-79 24-56 Total 1107470 941123 99816 66531 82-83 71-74 79-81 89-94 86-91 71-76 68-85 include publication repositories such as arXiv3, government offices, company websites as well as data directory services for financial

C reports and patents. Scanned documents were excluded wherever possible because they can be rotated or skewed. This would not allow us to perform annotation with rectangular bounding-boxes and therefore complicate the annotation process. Preparation work included uploading and parsing the sourced PDF documents in the Corpus Conversion Service (CCS) [22], a cloud-native platform which provides a visual annotation interface and allows for dataset inspection and analysis. The annotation interface of CCS is shown in Figure 3. The desired balance of pages between the different document categories was achieved by selective subsampling of pages with certain desired properties. For example, we made sure to include the title page of each document and bias the remaining page selection to those with figures or tables. The latter was achieved by leveraging pre-trained object detection models from PubLayNet, which helped us estimate how many figures and tables a given page contains. Phase 2: Label selection and guideline. We reviewed the collected documents and identified the most common structural features they exhibit. This was achieved by identifying recurrent layout elements and lead us to the definition of 11 distinct class labels.

Figure 3: Corpus Conversion Service annotation user interface. The PDF page is shown in the background, with overlaid text-cells (in darker shades). The annotation boxes can be drawn by dragging a rectangle over each segment with the respective label from the palette on the right. These 11 class labels are Caption, Footnote, Formula, List-item, Page footer, Page-header, Picture, Section-header, Table, Text, and Title. Critical factors that were considered for the choice of these class labels were (1) the overall occurrence of the label, (2) the specificity of the label, (3) recognisability on a single page (i.e. no need for context from previous or next page) and (4) overall coverage of the page. Specificity ensures that the choice of label is not ambiguous, we distributed the annotation workload and performed continuous while coverage ensures that all meaningful items on a page can quality controls. Phase one and two required a small team of experts be annotated. We refrained from class labels that are very specific only. For phases three and four, a group of 40 dedicated annotators to a document category, such as Abstract in the Scientific Articles were assembled and supervised. category. We also avoided class labels that are tightly linked to the Phase 1: Data selection and preparation. Our inclusion criteria for documents were described in Section 3. A large effort went in DocBank, are often only distinguishable by discriminating on into ensuring that all documents are free to use. The data sources

Figure 4: Table 1 from the DocLayNet paper in the original PDF (A), as rendered Markdown (B) and in JSON representation (C). Spanning table cells, such as the multi-column header "triple inter-annotator mAP@0.5-0.95 (%)", is repeated for each column in the Markdown representation (B), which guarantees that every data point can be traced back to row and column headings only by its grid coordinates in the table. In the JSON representation, the span information is reflected in the fields of each table cell (C).

![Image 0 (page 1)](embedded:p1_i0)

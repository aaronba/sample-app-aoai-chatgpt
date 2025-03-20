import JSZip from "jszip";
import { DOMParser } from "xmldom";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { processPdfToGridImage } from "./pdfToImage";

/**
 * Converts a PPTX file (Blob) into a PDF.
 * @param pptxBlob - The PPTX file as a Blob.
 * @returns A Promise that resolves to a PDF Blob.
 */
export async function pptxToImage(pptxBlob: Blob): Promise<string> {
    return new Promise(async (resolve, reject) => {
        try {
            // Read the PPTX file as an ArrayBuffer
            const reader = new FileReader();
            reader.readAsArrayBuffer(pptxBlob);
            reader.onload = async () => {
                const pptxArrayBuffer = reader.result as ArrayBuffer;

                // Load the PPTX file as a ZIP archive
                const zip = await JSZip.loadAsync(pptxArrayBuffer);

                // Define the XML namespace for accessing text nodes in PowerPoint slides
                const xmlNamespace = "http://schemas.openxmlformats.org/drawingml/2006/main";

                // Create a variable to accumulate extracted text
                let text = "";

                // Create a PDF in landscape mode
                const pdf = new jsPDF({ orientation: "landscape" });
                pdf.setFontSize(10);
                pdf.setFont("helvetica", "normal");

                // Iterate through each slide, parse its XML, extract text, and add it to the PDF
                const slideFiles = Object.keys(zip.files).filter((fileName) => fileName.startsWith("ppt/slides/slide"));
                for (const slideFile of slideFiles) {
                    const slideFileContent = zip.file(slideFile);
                    if (slideFileContent) {
                        const maxWidth = pdf.internal.pageSize.width; //- 20; 
                        const slideXml = await slideFileContent.async("text");
                        const slideDoc = new DOMParser().parseFromString(slideXml, "text/xml");
                        const textNodes = slideDoc.getElementsByTagNameNS(xmlNamespace, "t");

                        // Ensure every text node starts on a new line and every paragraph node starts after two lines
                        let slideText = "";
                        for (let i = 0; i < textNodes.length; i++) {
                            const parentNode = textNodes[i].parentNode;
                            // if (parentNode && parentNode.nodeName === "a:p") { // Paragraph node
                            //     slideText += "\n\n" + textNodes[i].textContent;
                            // } else { // Text node
                            //     slideText += "\n" + textNodes[i].textContent;
                            // }
                            slideText += "\n" + textNodes[i].textContent;
                        }

                        // Add slide text to the PDF with text wrapping and pagination
                        const lines = pdf.splitTextToSize(slideText, maxWidth); // Adjust width as needed
                        let y = 10;
                        for (const line of lines) {
                            if (y + 10 > pdf.internal.pageSize.height - 20) { // Adjust height as needed
                                pdf.addPage();
                                y = 10;
                            }
                            pdf.text(line.trim(), 10, y, { align: 'left' });
                            y += 10;
                        }

                        // Add images to the PDF at the appropriate position
                        const imageNodes = slideDoc.getElementsByTagNameNS(xmlNamespace, "blip");
                        for (let i = 0; i < imageNodes.length; i++) {
                            const imageId = imageNodes[i].getAttribute("r:embed");
                            const imageFile = zip.file(`ppt/media/${imageId}.jpeg`);
                            if (imageFile) {
                                const imageData = await imageFile.async("base64");
                                const img = new Image();
                                img.src = `data:image/jpeg;base64,${imageData}`;
                                const imageNode = imageNodes[i].parentNode?.parentNode as Element | null;
                                if (imageNode) {
                                    const x = parseFloat(imageNode.getAttribute("x") || "10");
                                    const y = parseFloat(imageNode.getAttribute("y") || "10");
                                    const width = parseFloat(imageNode.getAttribute("cx") || `${maxWidth}`);
                                    const height = parseFloat(imageNode.getAttribute("cy") || "100");
                                    pdf.addImage(img, "JPEG", x, y, width, height); // Adjust dimensions as needed
                                }
                            }
                        }

                        pdf.addPage(); // Add a new page for the next slide
                    }
                }

                // Convert PDF to Blob and return
                const pdfBlob = pdf.output("blob");
                const mergedImageBase64 = await processPdfToGridImage(pdfBlob, 1);

                resolve(mergedImageBase64);
            };

            reader.onerror = (error) => reject(error);
        } catch (error) {
            reject(error);
        }
    });
}



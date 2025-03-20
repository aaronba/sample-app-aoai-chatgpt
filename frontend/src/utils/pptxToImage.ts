import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import PPTX2Json from "pptx2json";
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
                const uint8Array = new Uint8Array(pptxArrayBuffer); // Ensures correct data format

                
                // Parse PPTX file to JSON format
                const pptxParser = new PPTX2Json();
                const pptxData = await pptxParser.toJson(uint8Array);

                const pdf = new jsPDF({
                    orientation: "landscape",
                    unit: "px",
                    format: [800, 600], // Adjust slide dimensions as needed
                });

                // Process slides
                for (let i = 0; i < pptxData.slides.length; i++) {
                    const slide = pptxData.slides[i];

                    // Create a temporary div to render the slide
                    const slideContainer = document.createElement("div");
                    slideContainer.style.width = "800px";
                    slideContainer.style.height = "600px";
                    slideContainer.style.position = "absolute";
                    slideContainer.style.visibility = "hidden";
                    document.body.appendChild(slideContainer);

                    // Render slide content dynamically
                    slideContainer.innerHTML = renderSlideToHTML(slide);

                    // Convert slide to an image
                    const slideCanvas = await html2canvas(slideContainer);
                    const imgData = slideCanvas.toDataURL("image/png");

                    // Add slide image to PDF
                    if (i > 0) pdf.addPage();
                    pdf.addImage(imgData, "PNG", 0, 0, 800, 600);

                    // Remove temporary container
                    document.body.removeChild(slideContainer);
                }

                // Convert PDF to Blob and return
                const pdfBlob = pdf.output("blob");
                const mergedImageBase64 = await processPdfToGridImage(pdfBlob, 1);
                
                return mergedImageBase64;
            };

            reader.onerror = (error) => reject(error);
        } catch (error) {
            reject(error);
        }
    });
}

/**
 * Renders a slide object as an HTML structure.
 * @param slide - Slide data from pptx2json.
 * @returns HTML string representing the slide.
 */
function renderSlideToHTML(slide: any): string {
    let html = `<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; background-color: ${slide.bgColor || 'white'};">`;

    slide.texts?.forEach((text: any) => {
        html += `<p style="font-size: ${text.fontSize}px; color: ${text.color};">${text.text}</p>`;
    });

    slide.images?.forEach((image: any) => {
        html += `<img src="${image.src}" style="max-width: 100%; max-height: 100%;" />`;
    });

    html += `</div>`;
    return html;
}

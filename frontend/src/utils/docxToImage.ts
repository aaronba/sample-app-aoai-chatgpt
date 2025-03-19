import { renderAsync } from 'docx-preview';
import { createCanvas, Image } from 'canvas';
import { jsPDF } from 'jspdf';
import { processPdfToGridImage } from './pdfToImage';
import html2canvas from 'html2canvas';

async function docxToImage(docxBlob: Blob): Promise<string> {
    const arrayBuffer = await docxBlob.arrayBuffer();
    const canvas = createCanvas(2480, 3508);
    const ctx = canvas.getContext('2d');

    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.left = "-9999px"; // Hide it from view
    document.body.appendChild(container);

    // Initialize jsPDF
    const pdf = new jsPDF("p", "mm", "a4");

    // Render DOCX file into HTML per page with page breaks
    await renderAsync(docxBlob, container, undefined, { ignoreLastRenderedPageBreak: false });
    const pages = container.querySelectorAll("section");

    for (const [index, page] of pages.entries()) {
        if (index > 0) {
            pdf.addPage(); // Add a new page for each section
        }

        const canvas = await html2canvas(page);
        const imgData = canvas.toDataURL("image/png");

        const imgWidth = 210; // A4 width in mm
        const imgHeight = (page.scrollHeight * imgWidth) / page.scrollWidth; // Maintain aspect ratio based on page content height

        pdf.addImage(imgData, "PNG", 0, 0, imgWidth, imgHeight);
    }

    const pdfBlob = pdf.output('blob');
    const mergedImageBase64 = await processPdfToGridImage(pdfBlob, 1);

    return mergedImageBase64;
}

export default docxToImage;

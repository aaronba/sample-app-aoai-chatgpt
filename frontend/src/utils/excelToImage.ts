import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import { processPdfToGridImage } from './pdfToImage';

export async function processexcelFileToImage(excelBlob: Blob): Promise<string> {
    // Read the Excel file from the Blob
    const arrayBuffer = await excelBlob.arrayBuffer();
    //const data = new Uint8Array(arrayBuffer);

    const options: XLSX.ParsingOptions = {
        type: 'array',         
        raw:false,
        dateNF: 'MM/dd/yyyy', // Specify the date format string here
      };
    const workbook = XLSX.read(arrayBuffer, options);

    // Create a new jsPDF instance
    const doc = new jsPDF();

    // Loop through all sheets
    workbook.SheetNames.forEach((sheetName, sheetIndex) => {
        if (sheetIndex > 0) {
            doc.addPage(); // Start each sheet on a new page
        }
        const worksheet = workbook.Sheets[sheetName];
        
        //const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1}) as any[][]; // Use dateNF to format date values
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, raw: false, dateNF: 'MM/dd/yyyy' }) as any[][]; // Use dateNF to format date values

        // Add sheet name as page title
        doc.setFontSize(16);
        doc.text(sheetName, 10, 10, { align: 'left' });
        doc.setFontSize(12);

        // Convert the JSON data to key-value pairs
        const headers = jsonData[0];
        const keyValueData = jsonData.slice(1).map(row => {
            const obj: any = {};
            row.forEach((cell, index) => {                 
                obj[headers[index]] = cell;
            });
            return obj;
        });

        // Set font and text alignment
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(12);

        // Draw the Excel data onto the PDF
        keyValueData.forEach((row: any, rowIndex: number) => {
            doc.addPage(); // Start each row on a new page
            let y = 20; // Adjust y position to start below the title
            const lineHeight = 10;
            const maxWidth = doc.internal.pageSize.width - 20;
            Object.keys(row).forEach((key: string, cellIndex: number) => {
                let text = `${key}: ${row[key]}`;
                let lines = doc.splitTextToSize(text, maxWidth); // Wrap text to fit within available width
                lines.forEach((line: string) => {
                    if (y + lineHeight > doc.internal.pageSize.height - 10) {
                        doc.addPage(); // Add a new page if content exceeds page height
                        y = 10;
                    }
                    doc.text(line, 10, y, { align: 'left' }); // Left align text
                    y += lineHeight; // Adjust y position for each line
                });
            });
            // Add page number
            const pageCount = doc.getNumberOfPages();
            doc.setFontSize(10);
            doc.text(`Page ${pageCount}`, doc.internal.pageSize.width - 20, doc.internal.pageSize.height - 10, { align: 'right' });
            doc.setFontSize(12);
        });
    });

    // Convert the PDF to a Blob
    const pdfBlob = doc.output('blob');

    // Call processPdfToGridImage to create a merged image
    const mergedImageBase64 = await processPdfToGridImage(pdfBlob, 3); // Remove empty pages

    // Return the merged image as a base64-encoded string
    return mergedImageBase64;
}


import * as XLSX from 'xlsx';
import { createCanvas,loadImage } from 'canvas';

export async function processexcelFileToImage(excelBlob: Blob): Promise<string> {
    // Read the Excel file from the Blob
    const arrayBuffer = await excelBlob.arrayBuffer();
    const data = new Uint8Array(arrayBuffer);
    const workbook = XLSX.read(data, { type: 'array' });
    const base64Images: string[] = [];

    // Loop through all sheets
    workbook.SheetNames.forEach((sheetName) => {
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as any[][];

        
        // Determine the maximum width needed for each column
        const columnWidths = jsonData[0].map((_, colIndex) => {
            return Math.max(...jsonData.map(row => (row[colIndex] ? row[colIndex].toString().length * 10 : 0)));
        });

       
        // Create a canvas for each sheet
        const canvasWidth = columnWidths.reduce((acc, width) => acc + width, 0) + 20;
        const canvasHeight = jsonData.length * 20 + 40;
        const canvas = createCanvas(canvasWidth, canvasHeight);
        const ctx = canvas.getContext('2d');


        // Set font and text alignment
        ctx.font = '16px Arial';
        ctx.textAlign = 'left';

        // Draw the Excel data onto the canvas
        jsonData.forEach((row: any[], rowIndex: number) => {
            let xOffset = 10;
            row.forEach((cell: any, cellIndex: number) => {
                ctx.fillText(cell, xOffset, rowIndex * 20 + 30);
                xOffset += columnWidths[cellIndex];
            });
        });

        // Convert the canvas to a base64-encoded image
        const base64Image = canvas.toDataURL('image/png');
        base64Images.push(base64Image);
    });

    // Load all base64 images to get their dimensions
    const images = await Promise.all(base64Images.map(base64Image => loadImage(base64Image)));


    // Calculate the dimensions for the merged canvas
    const columns = 4;
    const rows = Math.ceil(images.length / columns);
    const maxWidth = Math.max(...images.map(img => img.width));
    const maxHeight = Math.max(...images.map(img => img.height));
    const mergedCanvasWidth = maxWidth;// * columns;
    const mergedCanvasHeight = maxHeight * rows;


    // Create the merged canvas
    const mergedCanvas = createCanvas(mergedCanvasWidth, mergedCanvasHeight);
    const mergedCtx = mergedCanvas.getContext('2d');

    // Draw each base64 image onto the merged canvas
    for (let index = 0; index < base64Images.length; index++) {
        const img = await loadImage(base64Images[index]);
        const x = (index % columns) * img.width;
        const y = Math.floor(index / columns) * img.height;
        mergedCtx.drawImage(img, x, y, img.width, img.height);
    }


    // Return the merged canvas as a base64-encoded image
    return mergedCanvas.toDataURL('image/png');
}


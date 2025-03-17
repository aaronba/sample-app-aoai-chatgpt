import * as pdfjsLib from 'pdfjs-dist';
import workerSrc from 'pdfjs-dist/build/pdf.worker?worker&url'
import { createCanvas  } from 'canvas';

// Ensure that the worker is specified (using a CDN link or local path) 2.10.377
//pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.worker.min.mjs';
//pdfjsLib.GlobalWorkerOptions.workerSrc = 'pdfjs-dist/build/pdf.worker.mjs';
pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;



// Helper function to ensure the image is fully loaded
function loadImageAsync(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = (err) => reject(err);
    image.src = src;
  });
}

// Exporting the function to make it available for use elsewhere
export async function convertPdfToImages(pdfBlob: Blob): Promise<HTMLImageElement[]> {
  const pdfData = await pdfBlob.arrayBuffer();
  const pdf = await pdfjsLib.getDocument(pdfData).promise;
  const images: HTMLImageElement[] = [];

  // Loop through all the pages
  for (let i = 0; i < pdf.numPages; i++) {
    const page = await pdf.getPage(i + 1);
    const viewport = page.getViewport({ scale: 1 });

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('Failed to get canvas context');
    }
    
    let width = viewport.width;
    let height = viewport.height;

    const maxWidth = 800;
    // Calculate the new dimensions
    if (viewport.width > 800 || viewport.height > 600) {
      if (viewport.width > viewport.height) {
        height = (maxWidth / viewport.width) * viewport.height
        width = maxWidth
      } else {
        width = (600 / viewport.height) * viewport.width
        height = 800
      }
    }
    canvas.height = 800;//viewport.height;
    canvas.width = 600;//viewport.width;

    await page.render({ canvasContext: context, viewport }).promise;
    const image = new Image();
    image.src = canvas.toDataURL();
    
    // Wait for the image to load before adding it to the array
    const loadedImage = await loadImageAsync(image.src);
    images.push(loadedImage);
  }

  return images;
}

// Function to merge images into a grid with 4 columns and dynamic rows
export async function mergeImagesToGrid(images: HTMLImageElement[]): Promise<string> {
  const columns = 4; // 4 columns
  const rows = Math.ceil(images.length / columns); // Calculate the number of rows needed
  const imageSize = images[0].width; // Assume all images are the same size
  const canvas = createCanvas(imageSize * columns, imageSize * rows);
  const context = canvas.getContext('2d');
  let x = 0, y = 0;

  for (let i = 0; i < images.length; i++) {
    if (x >= columns) {
      x = 0;
      y++;
    }

    // Ensure the image is drawn on the canvas
    context?.drawImage(images[i] as any, x * imageSize, y * imageSize);
    x++;
  }

  // Return the merged canvas as a Base64 image
  // write the image to a file
  //fs.writeFileSync('c:\temp\merged_image.png', canvas.toBuffer('image/png'));

  return canvas.toDataURL();
}

// Main function to process PDF and return merged Base64 image
export async function processPdfToGridImage(pdfBlob: Blob): Promise<string> {
  // Convert PDF to images
  const images = await convertPdfToImages(pdfBlob);

  // Merge the images into a 4x4 grid and return as Base64 image
  return await mergeImagesToGrid(images);
}

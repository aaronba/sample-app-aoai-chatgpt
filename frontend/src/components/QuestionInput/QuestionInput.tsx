import { useContext, useState } from 'react'
import { FontIcon, Stack, TextField } from '@fluentui/react'
import { SendRegular } from '@fluentui/react-icons'

import Send from '../../assets/Send.svg'

import styles from './QuestionInput.module.css'
import { ChatMessage } from '../../api'
import { AppStateContext } from '../../state/AppProvider'
import { resizeImage } from '../../utils/resizeImage'

import { processPdfToGridImage } from '../../utils/pdfToImage';
import { processexcelFileToImage } from '../../utils/excelToImage';
import docxToImage from '../../utils/docxToImage';
import { pptxToImage } from '../../utils/pptxToImage';

interface Props {
  onSend: (question: ChatMessage['content'], id?: string) => void
  disabled: boolean
  placeholder?: string
  clearOnSend?: boolean
  conversationId?: string
}

export const QuestionInput = ({ onSend, disabled, placeholder, clearOnSend, conversationId }: Props) => {
  const [question, setQuestion] = useState<string>('')
  const [base64Images, setBase64Images] = useState<string[]>([]);
  const [placeholderText, setPlaceholderText] = useState<string>('');

  const appStateContext = useContext(AppStateContext)
  const OYD_ENABLED = appStateContext?.state.frontendSettings?.oyd_enabled || false;

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    setPlaceholderText('Adding files...'); // Show placeholder text

    const files = event.target.files;

    if (files) {
      const base64Array: string[] = [];
      for (const file of files) {
        if (file.type === 'application/pdf') {
          const mergedImageBase64 = await processPdfToGridImage(file);
          base64Array.push(mergedImageBase64);
        } 
        else if (file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || file.type === 'application/vnd.ms-excel') {
          const mergedExcelImage = await processexcelFileToImage(file);
          base64Array.push(mergedExcelImage);
        } 
        else if (file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
          const mergedDocxImage = await docxToImage(file);
          base64Array.push(mergedDocxImage);
        } 
        else if (file.type === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') {
          const mergedPptxImage = await pptxToImage(file);
          base64Array.push(mergedPptxImage);
        } 
        else {
          const base64 = await convertToBase64(file);
          base64Array.push(base64);
        }
      }
      setBase64Images(base64Array);
    }

    setPlaceholderText(''); // Hide placeholder text
  };

  const convertToBase64 = async (file: Blob): Promise<string> => {
    try {
      const resizedBase64 = await resizeImage(file, 800, 800);
      return resizedBase64;
    } catch (error) {
      console.error('Error:', error);
      return '';
    }
  };

  const sendQuestion = () => {
    if (disabled || !question.trim()) {
      return;
    }

    //Loop through the base64 images and convert them to the format required by the API
    const base64ImagesToSend: ChatMessage["content"] = [{ type: "text", text: question }, ...base64Images.map(image => ({ type: "image_url", image_url: { url: image,detail:"high"  } }))] as ChatMessage["content"];

    const questionContent: ChatMessage["content"] = base64Images.length > 0 
      ? base64ImagesToSend
      : question.toString();

    if (conversationId && questionContent !== undefined) {
      onSend(questionContent, conversationId);
      setBase64Images([]);
    } else {
      onSend(questionContent);
      setBase64Images([]);
    }

    if (clearOnSend) {
      setQuestion('');
    }
  };

  const onEnterPress = (ev: React.KeyboardEvent<Element>) => {
    if (ev.key === 'Enter' && !ev.shiftKey && !(ev.nativeEvent?.isComposing === true)) {
      ev.preventDefault();
      sendQuestion();
    }
  };

  const onQuestionChange = (_ev: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
    setQuestion(newValue || '');
  };

  const sendQuestionDisabled = disabled || !question.trim();

  return (
    <Stack horizontal className={styles.questionInputContainer}>
      <TextField
        className={styles.questionInputTextArea}
        placeholder={placeholder}
        multiline
        resizable={false}
        borderless
        value={question}
        onChange={onQuestionChange}
        onKeyDown={onEnterPress}
      />
       {placeholderText && (
        <div className={styles.placeholderText}>{placeholderText}</div>
      )}
      {!OYD_ENABLED && (
        <div className={styles.fileInputContainer}>
          <input
            type="file"
            id="fileInput"
            onChange={(event) => handleImageUpload(event)}
            accept="image/*,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation" multiple
            className={styles.fileInput}
          />
          <label htmlFor="fileInput" className={styles.fileLabel} aria-label='Upload File'>
            <FontIcon
              className={styles.fileIcon}
              iconName={'PhotoCollection'}
              aria-label='Upload File'
            />            
          </label>
          
        </div>
      )}
     
      {base64Images.length > 0 && base64Images.map((image, index) => (
        <img key={index} className={styles.uploadedImage} src={image} alt={`Uploaded Preview ${index + 1}`} />
      ))}
      <div
        className={styles.questionInputSendButtonContainer}
        role="button"
        tabIndex={0}
        aria-label="Ask question button"
        onClick={sendQuestion}
        onKeyDown={e => (e.key === 'Enter' || e.key === ' ' ? sendQuestion() : null)}>
        {sendQuestionDisabled ? (
          <SendRegular className={styles.questionInputSendButtonDisabled} />
        ) : (
          <img src={Send} className={styles.questionInputSendButton} alt="Send Button" />
        )}
      </div>
      <div className={styles.questionInputBottomBorder} />
    </Stack>
  );
};

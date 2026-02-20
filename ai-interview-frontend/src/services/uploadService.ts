// ai-interview-frontend/src/services/uploadService.ts

export class UploadService {
  
  static async uploadRecording(
    interviewId: number,
    videoBlob: Blob,
    timeline: any[],
    duration: number
  ): Promise<boolean> {
    const formData = new FormData();
    formData.append('video', videoBlob, 'recording.webm');
    formData.append('timeline', JSON.stringify(timeline));
    formData.append('duration', duration.toString());

    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('No authentication token');
    }

    try {
      console.log(`📤 Uploading ${(videoBlob.size / 1024 / 1024).toFixed(2)}MB video...`);

      const response = await fetch(
        `http://localhost:8000/api/recordings/interviews/${interviewId}/upload-recording`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const result = await response.json();
      console.log('✅ Upload complete:', result);
      return true;

    } catch (err: any) {
      console.error('❌ Upload error:', err);
      throw err;
    }
  }

  static async uploadWithProgress(
    interviewId: number,
    videoBlob: Blob,
    timeline: any[],
    duration: number,
    onProgress: (percent: number) => void
  ): Promise<boolean> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('video', videoBlob, 'recording.webm');
      formData.append('timeline', JSON.stringify(timeline));
      formData.append('duration', duration.toString());

      const token = localStorage.getItem('token');

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percent = (e.loaded / e.total) * 100;
          onProgress(percent);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          console.log('✅ Upload complete');
          resolve(true);
        } else {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload error'));
      });

      xhr.open(
        'POST',
        `http://localhost:8000/api/recordings/interviews/${interviewId}/upload-recording`
      );
      
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);
    });
  }
}

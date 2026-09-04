const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
export const apiUrl=(path:string)=>API_URL+path;
export async function apiFetch<T>(path:string,init?:RequestInit):Promise<T>{const response=await fetch(apiUrl(path),{...init,headers:{'Content-Type':'application/json',...init?.headers}});if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(typeof body.detail==='string'?body.detail:'Something went wrong.');}return response.json();}
export async function uploadPdf(file:File){const data=new FormData();data.append('file',file);const response=await fetch(apiUrl('/api/documents/upload'),{method:'POST',body:data});if(!response.ok)throw new Error('Unable to upload document.');return response.json() as Promise<{document_id:string;filename:string}>;}
export async function checkBackend(){return apiFetch<{status:string}>('/health');}

export async function sendFeedback(message: string, response: string, rating: 'positive' | 'negative') { return apiFetch<{success: boolean}>('/api/feedback', { method: 'POST', body: JSON.stringify({ message, response, rating }) }); }
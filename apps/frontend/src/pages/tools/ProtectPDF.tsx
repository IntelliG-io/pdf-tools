import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Download, Upload, Lock, Unlock, FileText } from 'lucide-react';
import { protectPdf, removeProtection, checkPdfProtection, downloadFile } from '@/services/api';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';

const ProtectPDF = () => {
  // File upload state
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Protection options state
  const [userPassword, setUserPassword] = useState('');
  const [ownerPassword, setOwnerPassword] = useState('');
  const [encryptionLevel, setEncryptionLevel] = useState('high');
  
  // Permissions state
  const [allowPrinting, setAllowPrinting] = useState(false);
  const [allowModifying, setAllowModifying] = useState(false);
  const [allowCopying, setAllowCopying] = useState(false);
  const [allowAnnotating, setAllowAnnotating] = useState(false);
  const [allowFillingForms, setAllowFillingForms] = useState(false);
  
  // Remove protection state
  const [removePassword, setRemovePassword] = useState('');
  
  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  
  // Protection info state
  const [protectionInfo, setProtectionInfo] = useState<any>(null);
  
  // Handle file selection
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] || null;
    setFile(selectedFile);
    
    if (selectedFile) {
      try {
        setIsProcessing(true);
        const info = await checkPdfProtection(selectedFile);
        setProtectionInfo(info);
      } catch (error) {
        console.error('Error checking protection:', error);
        toast.error('Failed to check if PDF is protected');
      } finally {
        setIsProcessing(false);
      }
    } else {
      setProtectionInfo(null);
    }
  };
  
  // Handle protect PDF
  const handleProtectPdf = async () => {
    if (!file) {
      toast.error('Please select a PDF file first');
      return;
    }
    
    if (!userPassword) {
      toast.error('User password is required');
      return;
    }
    
    try {
      setIsProcessing(true);
      
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => (prev < 90 ? prev + 10 : prev));
      }, 300);
      
      const options = {
        userPassword,
        ownerPassword: ownerPassword || userPassword, // Use user password if owner password is not provided
        encryptionLevel,
        allowPrinting,
        allowModifying,
        allowCopying,
        allowAnnotating,
        allowFillingForms,
      };
      
      const protectedPdf = await protectPdf(file, options);
      
      clearInterval(progressInterval);
      setProgress(100);
      
      // Download the protected PDF
      downloadFile(protectedPdf, `${file.name.replace('.pdf', '')}_protected.pdf`);
      
      toast.success('PDF protected successfully');
    } catch (error: any) {
      console.error('Error protecting PDF:', error);
      toast.error(error.message || 'Failed to protect PDF');
    } finally {
      setIsProcessing(false);
      setProgress(0);
    }
  };
  
  // Handle remove protection
  const handleRemoveProtection = async () => {
    if (!file) {
      toast.error('Please select a PDF file first');
      return;
    }
    
    if (!removePassword) {
      toast.error('Password is required to remove protection');
      return;
    }
    
    try {
      setIsProcessing(true);
      
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => (prev < 90 ? prev + 10 : prev));
      }, 300);
      
      const unprotectedPdf = await removeProtection(file, removePassword);
      
      clearInterval(progressInterval);
      setProgress(100);
      
      // Download the unprotected PDF
      downloadFile(unprotectedPdf, `${file.name.replace('.pdf', '')}_unprotected.pdf`);
      
      toast.success('PDF protection removed successfully');
    } catch (error: any) {
      console.error('Error removing protection:', error);
      toast.error(error.message || 'Failed to remove PDF protection');
    } finally {
      setIsProcessing(false);
      setProgress(0);
    }
  };
  
  return (
    <div className="container mx-auto py-10">
      <div className="flex flex-col items-center justify-center space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">Protect PDF</h1>
          <p className="text-muted-foreground">
            Add password protection to your PDF files or remove existing protection
          </p>
        </div>
        
        <Card className="w-full max-w-3xl">
          <CardHeader>
            <CardTitle>Select PDF File</CardTitle>
            <CardDescription>
              Upload the PDF file you want to protect or unprotect
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid w-full items-center gap-4">
              <div className="flex flex-col space-y-1.5">
                <Label htmlFor="pdfFile">PDF File</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="pdfFile"
                    type="file"
                    accept=".pdf"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    className="flex-grow"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="h-4 w-4" />
                  </Button>
                </div>
                {file && (
                  <div className="text-sm mt-2">
                    Selected file: <span className="font-semibold">{file.name}</span>
                  </div>
                )}
              </div>
              
              {protectionInfo && (
                <Alert className={protectionInfo.isEncrypted ? "bg-amber-100" : "bg-green-100"}>
                  <FileText className="h-4 w-4" />
                  <AlertDescription>
                    {protectionInfo.isEncrypted 
                      ? 'This PDF is password protected.' 
                      : 'This PDF is not password protected.'}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </CardContent>
        </Card>
        
        <Tabs defaultValue="protect" className="w-full max-w-3xl">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="protect">Protect PDF</TabsTrigger>
            <TabsTrigger value="remove">Remove Protection</TabsTrigger>
          </TabsList>
          
          <TabsContent value="protect">
            <Card>
              <CardHeader>
                <CardTitle>Protect PDF with Password</CardTitle>
                <CardDescription>
                  Add password protection and set permissions for your PDF
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid w-full items-center gap-4">
                  {/* Password Settings */}
                  <div className="flex flex-col space-y-1.5">
                    <Label htmlFor="userPassword">User Password</Label>
                    <Input
                      id="userPassword"
                      type="password"
                      placeholder="Enter password for opening the PDF"
                      value={userPassword}
                      onChange={(e) => setUserPassword(e.target.value)}
                    />
                  </div>
                  
                  <div className="flex flex-col space-y-1.5">
                    <Label htmlFor="ownerPassword">
                      Owner Password (Optional)
                    </Label>
                    <Input
                      id="ownerPassword"
                      type="password"
                      placeholder="Password for changing permissions (defaults to user password)"
                      value={ownerPassword}
                      onChange={(e) => setOwnerPassword(e.target.value)}
                    />
                  </div>
                  
                  {/* Encryption Level */}
                  <div className="flex flex-col space-y-1.5">
                    <Label htmlFor="encryptionLevel">Encryption Level</Label>
                    <Select
                      value={encryptionLevel}
                      onValueChange={setEncryptionLevel}
                    >
                      <SelectTrigger id="encryptionLevel">
                        <SelectValue placeholder="Select encryption level" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low (40-bit RC4)</SelectItem>
                        <SelectItem value="medium">Medium (128-bit RC4)</SelectItem>
                        <SelectItem value="high">High (256-bit AES)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Permissions */}
                  <div className="space-y-3">
                    <Label>Permissions</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="allowPrinting"
                          checked={allowPrinting}
                          onCheckedChange={(checked) => setAllowPrinting(checked === true)}
                        />
                        <label
                          htmlFor="allowPrinting"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Allow Printing
                        </label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="allowModifying"
                          checked={allowModifying}
                          onCheckedChange={(checked) => setAllowModifying(checked === true)}
                        />
                        <label
                          htmlFor="allowModifying"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Allow Modifying
                        </label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="allowCopying"
                          checked={allowCopying}
                          onCheckedChange={(checked) => setAllowCopying(checked === true)}
                        />
                        <label
                          htmlFor="allowCopying"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Allow Copying
                        </label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="allowAnnotating"
                          checked={allowAnnotating}
                          onCheckedChange={(checked) => setAllowAnnotating(checked === true)}
                        />
                        <label
                          htmlFor="allowAnnotating"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Allow Annotations
                        </label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="allowFillingForms"
                          checked={allowFillingForms}
                          onCheckedChange={(checked) => setAllowFillingForms(checked === true)}
                        />
                        <label
                          htmlFor="allowFillingForms"
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                        >
                          Allow Form Filling
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex justify-between">
                {isProcessing && (
                  <div className="w-full mb-4">
                    <Progress value={progress} className="w-full" />
                  </div>
                )}
                <Button
                  onClick={handleProtectPdf}
                  disabled={!file || !userPassword || isProcessing}
                  className="w-full"
                >
                  <Lock className="mr-2 h-4 w-4" />
                  {isProcessing ? 'Processing...' : 'Protect PDF'}
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>
          
          <TabsContent value="remove">
            <Card>
              <CardHeader>
                <CardTitle>Remove Password Protection</CardTitle>
                <CardDescription>
                  Remove password protection from a PDF file
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col space-y-1.5">
                  <Label htmlFor="removePassword">PDF Password</Label>
                  <Input
                    id="removePassword"
                    type="password"
                    placeholder="Enter the password of the protected PDF"
                    value={removePassword}
                    onChange={(e) => setRemovePassword(e.target.value)}
                  />
                </div>
              </CardContent>
              <CardFooter className="flex justify-between">
                {isProcessing && (
                  <div className="w-full mb-4">
                    <Progress value={progress} className="w-full" />
                  </div>
                )}
                <Button
                  onClick={handleRemoveProtection}
                  disabled={!file || !removePassword || isProcessing}
                  className="w-full"
                >
                  <Unlock className="mr-2 h-4 w-4" />
                  {isProcessing ? 'Processing...' : 'Remove Protection'}
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default ProtectPDF;

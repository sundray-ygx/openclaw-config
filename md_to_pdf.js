const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

async function convertMarkdownToPDF(inputFile, outputFile) {
    const markdown = fs.readFileSync(inputFile, 'utf-8');
    
    // 简单的Markdown转HTML
    let html = markdown
        .replace(/^# (.*$)/gm, '<h1 style="color:#1a1a1a;font-size:24px;margin-bottom:20px;border-bottom:2px solid #333;padding-bottom:10px;">$1</h1>')
        .replace(/^## (.*$)/gm, '<h2 style="color:#2c2c2c;font-size:18px;margin-top:25px;margin-bottom:12px;border-left:4px solid #4a90d9;padding-left:10px;">$1</h2>')
        .replace(/^### (.*$)/gm, '<h3 style="color:#3d3d3d;font-size:15px;margin-top:18px;margin-bottom:8px;">$1</h3>')
        .replace(/^#### (.*$)/gm, '<h4 style="color:#4d4d4d;font-size:14px;margin-top:15px;margin-bottom:6px;">$1</h4>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^\|(.*)\|$/gm, (match) => {
            const cells = match.split('|').filter(c => c.trim());
            return '<tr>' + cells.map(c => `<td style="border:1px solid #ddd;padding:8px;">${c.trim()}</td>`).join('') + '</tr>';
        })
        .replace(/(<tr>.*<\/tr>\n?)+/g, '<table style="border-collapse:collapse;width:100%;margin:15px 0;font-size:13px;">$&</table>')
        .replace(/^- (.*$)/gm, '<li style="margin:6px 0;line-height:1.6;">$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/g, '<ul style="margin:10px 0;padding-left:20px;">$&</ul>')
        .replace(/\n\n/g, '</p><p style="line-height:1.6;margin:10px 0;">')
        .replace(/^([^<].*)/gm, '<p style="line-height:1.6;margin:10px 0;">$1</p>');
    
    const fullHTML = `
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body { font-family: "Microsoft YaHei", "SimHei", sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #333; font-size: 14px; }
            h1 { text-align: center; }
            table { page-break-inside: avoid; }
            tr:nth-child(even) { background: #f9f9f9; }
            th { background: #4a90d9; color: white; }
        </style>
    </head>
    <body>
        ${html}
    </body>
    </html>`;
    
    const browser = await puppeteer.launch({
        executablePath: '/usr/lib64/chromium-browser/headless_shell',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setContent(fullHTML, { waitUntil: 'networkidle0' });
    await page.pdf({
        path: outputFile,
        format: 'A4',
        printBackground: true,
        margin: { top: '20mm', right: '20mm', bottom: '20mm', left: '20mm' }
    });
    
    await browser.close();
    console.log('PDF generated:', outputFile);
}

const inputFile = process.argv[2] || '/root/.openclaw/workspace/output/严国贤_研发总监_简历_优化版.md';
const outputFile = process.argv[3] || '/root/.openclaw/workspace/archive/resume/严国贤_研发总监_简历_优化版.pdf';

convertMarkdownToPDF(inputFile, outputFile).catch(console.error);

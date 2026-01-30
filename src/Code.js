function createContracts() {
  // 1. 사장님이 준비하신 파일 ID (자동 입력됨)
  const TEMPLATE_ID = '12fECBOzHWcGTZSny6lT9kneOEKMV6WAzs4r9X_HWk1w'; // 근로계약서 템플릿
  const SHEET_ID = '17qI95hMU68rnd4QjTt1yFmV0Llgl-NDKrMhaJWCkBc4';    // 직원 명부 시트

  // 2. 파일 열기
  const templateFile = DriveApp.getFileById(TEMPLATE_ID);
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];
  const data = sheet.getDataRange().getValues(); // 시트 전체 데이터 가져오기

  // 3. 헤더(첫 줄)와 데이터 분리
  const headers = data[0]; // 예: ['이름', '시급', '주소' ...]
  const rows = data.slice(1);

  // 4. 계약서 생성 반복문
  rows.forEach(function(row, index) {
    const name = row[0]; // 첫 번째 칸(A열)을 이름으로 가정
    if (!name) return;   // 이름 없으면 패스

    // 4-1. 템플릿 복사해서 새 파일 만들기
    const newFile = templateFile.makeCopy(name + '님의 근로계약서');
    const newDoc = DocumentApp.openById(newFile.getId());
    const body = newDoc.getBody();

    // 4-2. 구멍 메우기 (치환)
    // 시트의 모든 열을 돌면서 {{헤더이름}}을 찾아 데이터로 바꿈
    headers.forEach(function(header, i) {
      body.replaceText('{{' + header + '}}', row[i]);
    });

    // 4-3. 저장 및 닫기
    newDoc.saveAndClose();
    console.log(name + '님 계약서 생성 완료!');
  });
}

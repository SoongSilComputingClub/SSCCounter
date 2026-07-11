## Code Style Check

SSCCounter는 monorepo 구조로 FE, BE, Embedded 코드를 함께 관리합니다.  
PR 생성 시 GitHub Actions에서 각 영역의 코드 스타일 검사를 자동으로 수행합니다.

### Backend

Backend는 Ruff를 사용합니다.

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m ruff format --check .
```

자동 수정:
```bash
python -m ruff check. --fix
python -m ruff format .
```

### Frontend

Frontend는 Prettier를 사용합니다.
```bash
cd frontend
npm install
npm run format:check
```

자동 수정:
```
npm run format
```

### Embedded

Embedded는 clang-format을 사용합니다.
```bash
git ls-files 'embedded/ssccam/**/*.c' 'embedded/ssccam/**/*.h' \
  | xargs clang-format --dry-run -Werror
```

자동 수정:
```bash
git ls-files 'embedded/ssccam/**/*.c' 'embedded/ssccam/**/*.h' \
  | xargs clang-format -i
```

### PR 전 확인

```bash
cd backend
python -m ruff check .
python -m ruff format --check .

cd ../frontend
npm run format:check

cd ..
git ls-files 'embedded/ssccam/**/*.c' 'embedded/ssccam/**/*.h' \
  | xargs clang-format --dry-run -Werror
```
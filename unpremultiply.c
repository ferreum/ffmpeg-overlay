#include <stdio.h>

// Translate rawvideo with premultiplied alpha to non-premultiplied alpha.

int main(int argc, char *argv[]) {
    if (argc > 1) {
        fprintf(stderr, "%s: too many arguments\n", argv[0]);
    }
    unsigned char buf[BUFSIZ];
    size_t n;
    unsigned int r, g, b, a;
    float f;
    while (!feof(stdin) && (n = fread(buf, 4, BUFSIZ / 4, stdin)) != 0) {
        unsigned char *p = buf;
        unsigned char *e = buf + n * 4;
        for (; p < e; p += 4) {
            a = p[3];
            if (a > 0 && a < 255) {
                f = 255.0f / (float) a;
                r = (int) ((float) p[0] * f);
                g = (int) ((float) p[1] * f);
                b = (int) ((float) p[2] * f);
                if (r < 255) p[0] = r; else p[0] = 255;
                if (g < 255) p[1] = g; else p[1] = 255;
                if (b < 255) p[2] = b; else p[2] = 255;
            }
        }
        if (fwrite(buf, 4, n, stdout) != n) {
            if (ferror(stdout)) {
                perror("fwrite");
            }
            return 1;
        }
    }
    if (ferror(stdin)) {
        perror("fread");
        return 1;
    }
    return 0;
}

class SpringInit < Formula
  desc "CLI for generating Spring Boot projects from start.spring.io"
  homepage "https://github.com/your-org/spring-initializr-cli"
  url "__URL__"
  sha256 "__SHA256__"
  version "__VERSION__"

  depends_on "python@3.12"

  def install
    libexec.install Dir["*"]
    bin.install_symlink libexec/"bin/spring-init" => "spring-init"
  end

  test do
    assert_match "spring-init", shell_output("#{bin}/spring-init --help")
  end
end
